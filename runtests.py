#This file mainly exists to allow python setup.py test to work.
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'emencia.django.newsletter.testsettings'
test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, test_dir)

import django
from django.test.utils import get_runner
from django.conf import settings

def runtests():
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True)
    failures = test_runner.run_tests(['emencia'])
    sys.exit(bool(failures))

    # test_runner = get_runner(settings)
    # failures = test_runner([], verbosity=1, interactive=True)
    # sys.exit(failures)

if __name__ == '__main__':
    runtests()