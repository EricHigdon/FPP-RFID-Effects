import os
import sys
import time
from copy import copy
from tinydb import TinyDB, Query

USE_ENCRYPTION = '--no-encryption' not in sys.argv
USE_ARGON = '--argon' in sys.argv
USE_RFID = '--use-names' not in sys.argv
USE_MFRC  = '--use-mfrc' in sys.argv
USE_SERIAL = '--use-serial' in sys.argv

if USE_ENCRYPTION and not USE_ARGON:
    PEPPER = os.getenv('FPP_PEPPER')
    if PEPPER is None:
        raise Exception('FPP_PEPPER environment variable is not defined')

if not USE_RFID and (USE_MFRC or USE_SERIAL):
    raise Exception(
        '"{}" and "--use-names" cannot be used together'.format(
	    '--use-mfrc' if USE_MFRC else '--use-serial'
	)
    )

if not USE_ENCRYPTION and USE_ARGON:
    raise Exception(
	'"--argon" and "--no-encryption" cannot be used together'
    )

if USE_ENCRYPTION:
    from passlib.hash import argon2
    import hashlib, binascii

class BaseReader:

    def wait(self):
        if hasattr(self, '_running'):
            time.sleep(1)
        else:
            self._running = True

    def get_db_path(self):
        suffix = ''
        if not USE_ENCRYPTION:
            suffix = '_insecure'
        if USE_ARGON:
            suffix = '_argon'
        return 'db_profiles_{}{}.json'.format(
            self.__class__.__name__.lower(),
            suffix
        )

    def read(self):
        self.wait()
        print('Waiting for RFID scan...')

    def get_hash(self, value):
        """Hash a value for storing or validating"""
        pepper = hashlib.sha256(PEPPER.encode('ascii')).hexdigest().encode('ascii')
        valhash = hashlib.pbkdf2_hmac('sha512', value.encode('utf-8'), pepper, 200000)
        valhash = binascii.hexlify(valhash)
        return (pepper + valhash).decode('ascii')

    def update_profile(self, profile, **kwargs):
        Profile = Query()
        profiles.update(kwargs, Profile.id == profile['id'])

    def get_argon_profile(self, id):
        for profile in profiles.all():
            if argon2.verify(id, profile['id']):
                print('Loading profile: {}'.format(profile['name']))
                if not USE_ARGON:
                    print('converting profile to non-argon encryption')
                    self.update_profile(profile, id=self.get_hash(id))
                return profile

    def get_profile(self, id, key=None):
        final_id = id
        if not USE_ARGON or USE_MFRC:
            if USE_ENCRYPTION and not USE_ARGON and not USE_MFRC:
                final_id = self.get_hash(id)
            Profile = Query()
            profile = profiles.search(Profile.id == final_id)
            if profile:
                profile = profile[0]
                if USE_ARGON and USE_MFRC and not argon2.verify(key, profile['key']):
                    return None
                elif USE_MFRC and self.get_hash(key) != profile['key']:
                    return None
                print('Loading profile: {}'.format(profile['name']))
                return profile
        if USE_ARGON or (USE_ENCRYPTION and not profile):
            return self.get_argon_profile(id)

        return None

    def cleanup(self):
        pass

class MFRCReader(BaseReader):
    def __init__(self):
        from RPi import GPIO
        self.GPIO = GPIO
        from mfrc522 import SimpleMFRC522 as rfid
        self.reader = rfid()
	
    def read(self):
        super().read()
        return self.reader.read()

    def cleanup(self):
        self.GPIO.cleanup()

class SerialReader(BaseReader):
    def __init__(self):
        import serial
        self.reader = serial.Serial('/dev/serial0', 9600, timeout=1)

    def read(self):
        super().read()
        id = ''
        while len(id) == 0:
            id = self.reader.read(12)
            return id, None

class WiegandReader(BaseReader):
    value = ''

    def __init__(self):
        import pigpio
        import wiegand
        pi = pigpio.pi()
        self.reader = wiegand.decoder(pi, 14, 15, self.wiegand_callback)

    def wiegand_callback(self, bits, value):
        self.value = str(value)
	
    def read(self):
        super().read()
        while True:
            if len(self.value) > 0:
                value = copy(self.value)
                self.value = ''
                return value, None

    def cleanup(self):
        self.reader.cancel()

class NameReader(BaseReader):
    def read(self):
        return input('ID: '), None


if USE_MFRC:
    reader = MFRCReader()
elif not USE_RFID:
    reader = NameReader()
elif USE_SERIAL:
    reader = SerialReader()
else:
    reader = WiegandReader()

EFFECTS = [
    'blue',
    'blue_green_plasma',
    'blue_meteors',
    'blue_up',
    'candy_cane',
    'fire',
    'green',
    'green_bounce',
    'purple',
    'purple_life',
    'rainbow_butterfly',
    'rainbow_cycle',
    'rainbow_plasma',
    'rainbow_twinkle',
    'rainbow_wave',
    'red',
    'snowing',
    'us_strobe',
    'white',
    'white_twinkle'
]

DEFAULT_EFFECT = EFFECTS[0]
profiles_path = os.path.join(
    os.path.dirname(__file__),
    reader.get_db_path()
)
profiles = TinyDB(profiles_path)

def start_effect(effect):
    cmd = 'fpp -e "{}",1,1'.format(effect)
    os.system(cmd)

def kill_effect(effect):
    cmd = 'fpp -E "{}"'.format(effect)
    os.system(cmd)
	
def create_profile(id, key=None):
    name = input('Enter the new user\'s name: ')
    print('Available effects:')
    for effect in EFFECTS:
        print(effect)
    effect = input('Choose an effect for the new user: ')
    profile = {
        'id': id,
	'name': name,
	'effect': effect
    }
    if USE_ARGON and key is not None:
        profile['key'] = argon2.hash(key)
    elif USE_ENCRYPTION and key is not None:
        profile['key'] = reader.get_hash(id)
    elif USE_ARGON:
        profile['id'] = argon2.hash(id)
    elif USE_ENCRYPTION:
        profile['id'] = reader.get_hash(id)
    profiles.insert(profile)
    return profile

def main():
    old_effect = None
    try:
        for effect in EFFECTS:
            kill_effect(effect)
        while True:
            id, key = reader.read()
            profile = reader.get_profile(id, key)
            if profile is not None:
                effect = profile.get('effect', DEFAULT_EFFECT)
                if old_effect is not None:
                    kill_effect(old_effect)
                start_effect(effect)
                old_effect = effect
            else:
                print('No user with that ID extists')
                if input('Would you like to create a new user (y/n)? ').lower() == 'y':
                    profile = create_profile(id, key)
                    effect = profile.get('effect', DEFAULT_EFFECT)
                    if old_effect is not None:
                        kill_effect(old_effect)
                    start_effect(effect)
                    old_effect = effect
    except KeyboardInterrupt:
        print('\nExiting...')
    finally:
        reader.cleanup()
        if old_effect is not None:
            kill_effect(old_effect)

main()
