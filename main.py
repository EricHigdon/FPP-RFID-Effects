import os
import sys
from tinydb import TinyDB, Query

USE_ENCRYPTION = '--no-encryption' not in sys.argv
USE_RFID = '--no-rfid' not in sys.argv

if USE_ENCRYPTION:
	from passlib.hash import argon2

if USE_RFID:
	from RPi import GPIO
	from mfrc522 import SimpleMFRC522 as rfid
	reader = rfid()

EFFECTS = [
	'blue',
	'purple'
]

DEFAULT_EFFECT = EFFECTS[0]
profiles = TinyDB(os.path.join(os.path.dirname(__file__), 'profiles.json'))

def start_effect(effect):
	cmd = 'fpp -e {},1,1'.format(effect)
	os.system(cmd)

def kill_effect(effect):
	cmd = 'fpp -E {}'.format(effect)
	os.system(cmd)
	
def get_profile(id):
	
	if USE_ENCRYPTION and not USE_RFID:
		for profile in profiles.all():
			if argon2.verify(id, profile['id']):
				print('Loading profile: {}'.format(profile['name']))
				return profile
	else:
		Profile = Query()
		profile = profiles.search(Profile.id == id)
		if profile:
			profile = profile[0]
			if USE_ENCRYPTION and not argon2.verify(id, profile['key']):
				return None
			print('Loading profile: {}'.format(profile['name']))
			return profile
	return None

def create_profile(id):
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
			if USE_RFID:
				print('Waiting for RFID scan...')
				id, code = reader.read()
			else:
				id = input('ID: ')
			profile = get_profile(id)
			if profile is not None:
				effect = profile.get('effect', DEFAULT_EFFECT)
				if old_effect is not None:
					kill_effect(old_effect)
				start_effect(effect)
				old_effect = effect
			else:
				print('No user with that ID extists')
				if input('Would you like to create a new user (y/n)? ').lower() == 'y':
					create_profile(id)
	except KeyboardInterrupt:
		print('\nExiting...')
	finally:
		if USE_RFID:
			GPIO.cleanup()
		if old_effect is not None:
			kill_effect(old_effect)

main()
