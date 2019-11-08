import os

DEFAULT_EFFECT = 'purple'
PROFILES = {
	'Eric': {
		'effect': 'blue'
	}
}

def start_effect(effect):
	cmd = 'fpp -e {},1,1'.format(effect)
	os.system(cmd)

def kill_effect(effect):
	cmd = 'fpp -E {}'.format(effect)
	os.system(cmd)

def create_user(id):
	

def main():
	old_effect = None
	try:
		for profile in PROFILES.values():
			kill_effect(profile.get('effect', DEFAULT_EFFECT))
		kill_effect(DEFAULT_EFFECT)
		while True:
			id = input('ID: ')
			profile = PROFILES.get(id, None)
			if profile is not None:
				effect = profile.get('effect', DEFAULT_EFFECT)
				if old_effect is not None:
					kill_effect(old_effect)
				start_effect(effect)
				old_effect = effect
			else:
				print('No user with that ID extists')
				new_user = input('Would you like to create a new user (y/n)?')
				if new_user == 'y':
					create_user(id)
	except KeyboardInterrupt:
		print('\nExiting...')
	finally:
		if old_effect is not None:
			kill_effect(old_effect)

main()
