import os
from passlib.hash import argon2

EFFECTS = [
	'blue',
	'purple'
]

DEFAULT_EFFECT = EFFECTS[0]
PROFILES = {}

def start_effect(effect):
	cmd = 'fpp -e {},1,1'.format(effect)
	os.system(cmd)

def kill_effect(effect):
	cmd = 'fpp -E {}'.format(effect)
	os.system(cmd)
	
def get_profile(id):
	for key, profile in PROFILES.items():
		if argon2.verify(id, key):
			print('Loading profile: {}'.format(profile['name']))
			return profile
	return None

def create_profile(id):
	id = argon2.hash(id)
	name = input('Enter the new user\'s name: ')
	print('Available effects:')
	for effect in EFFECTS:
		print(effect)
	effect = input('Choose an effect for the new user: ')
	PROFILES[id] = {
		'name': name,
		'effect': effect
	}

def main():
	old_effect = None
	try:
		for effect in EFFECTS:
			kill_effect(effect)
		while True:
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
		if old_effect is not None:
			kill_effect(old_effect)

main()
