import os
import sys
import time
from tinydb import TinyDB, Query

USE_ENCRYPTION = '--no-encryption' not in sys.argv
USE_RFID = '--use-names' not in sys.argv
USE_MFRC  = '--use-mfrc' in sys.argv

if not USE_RFID and USE_MFRC:
	raise Exception('MFRC is a RFID reader, so "--use-mfrc" and "--use-names" cannot be used together')

class BaseReader:

	def wait(self):
		if hasattr(self, '_running'):
			time.sleep(1)
		else:
			self._running = True

	def get_db_path(self):
		return 'db_profiles_{}{}.json'.format(
			self.__class__.__name__.lower(),
			'_insecure' if not USE_ENCRYPTION else ''
		)
	
	def get_profile(self, id, key=None):
		
		if USE_ENCRYPTION and not USE_MFRC:
			for profile in profiles.all():
				if argon2.verify(id, profile['id']):
					print('Loading profile: {}'.format(profile['name']))
					return profile
		else:
			Profile = Query()
			profile = profiles.search(Profile.id == id)
			if profile:
				profile = profile[0]
				if USE_ENCRYPTION and USE_MFRC and not argon2.verify(key, profile['key']):
					return None
				print('Loading profile: {}'.format(profile['name']))
				return profile
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
		self.wait()
		print('Waiting for RFID scan...')
		return self.reader.read()

	def get_db_path(self):
		return super().get_db_path().format(
			'_mfrc{}'.format(
				'_insecure' if not USE_ENCRYPTION else ''
			)
		)

	def cleanup(self):
		self.GPIO.cleanup()

class SerialReader(BaseReader):
	def __init__(self):
		import serial
		if self.is_rpi_3():
			self.reader = serial.Serial('/dev/ttyS0', 9600, timeout=1)
		else:
			self.reader = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)

	def read(self):
		self.wait()
		print('Waiting for RFID scan...')
		return self.reader.read(12), None

	def get_db_path(self):
		return super().get_db_path().format(
			'_serial{}'.format(
				'_insecure' if not USE_ENCRYPTION else ''
			)
		)
		
	def is_rpi_3(self):
		with open('/proc/device-tree/model', 'r') as version:
			return 'Raspberry Pi 3' in version.readline()

class NameReader(BaseReader):
	def read(self):
		return input('ID: '), None

if USE_ENCRYPTION:
	from passlib.hash import argon2

if USE_MFRC:
	reader = MFRCReader()
elif not USE_RFID:
	reader = NameReader()
else:
	reader = SerialReader()

EFFECTS = [
	'blue',
	'purple'
]

DEFAULT_EFFECT = EFFECTS[0]
profiles_path = os.path.join(
	os.path.dirname(__file__),
	reader.get_db_path()
)
profiles = TinyDB(profiles_path)

def start_effect(effect):
	cmd = 'fpp -e {},1,1'.format(effect)
	os.system(cmd)

def kill_effect(effect):
	cmd = 'fpp -E {}'.format(effect)
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
	if USE_ENCRYPTION and key is not None:
		profile['key'] = argon2.hash(key)
	elif USE_ENCRYPTION:
		profile['id'] = argon2.hash(id)
	profiles.insert(profile)

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
					create_profile(id, key)
	except KeyboardInterrupt:
		print('\nExiting...')
	finally:
		reader.cleanup()
		if old_effect is not None:
			kill_effect(old_effect)

main()
