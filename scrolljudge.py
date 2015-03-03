# usage: monkeyrunner scrolljudge.py

# adjust the variables below depending on the app under test and the
# environment.

from com.android.monkeyrunner import MonkeyRunner, MonkeyDevice

import os
import commands
import sys
import subprocess

os.chdir(os.path.dirname(os.path.realpath(__file__)))

python_path = 'python2'
android_sdk_path = os.environ['ANDROID_HOME']
app_id = 'com.willowtree.worstlistviewever'
app_path = 'app/build/outputs/apk/app-debug.apk'
systrace_output = "app/build/outputs/systrace.html"

print "waiting for adb"
device = MonkeyRunner.waitForConnection()

apk_path = device.shell('pm path ' + app_id)

if apk_path.startswith('package:'):
    print "deleting existing apk"
    device.removePackage(app_id)

print "installing apk"
device.installPackage(app_path)

print "launching app"
device.startActivity(component=app_id + '/' + app_id + '.MainActivity')

print "starting systrace"
systrace = subprocess.Popen(
    python_path + ' ' + android_sdk_path + '/platform-tools/systrace/systrace.py --time 5 -o ' + systrace_output + ' view',
    shell=True,
    cwd=os.getcwd(),
    stderr=subprocess.STDOUT)

# Wait for app to launch
MonkeyRunner.sleep(1)

width = int(device.getProperty('display.width'))
height = int(device.getProperty('display.height'))

for i in range(0, 8):
    device.drag((width / 2, height - 100), (width / 2, 100), 0.8)

print "waiting for systrace"
if systrace.wait() != 0:
    print "deleting apk"
    device.removePackage(app_id)
    sys.exit(1)

# We need the pid of the app to filter the systrace result before uninstalling 
# it
pid = int(device.shell('pgrep ' + app_id))
print "pid: " + str(pid)

print "deleting apk"
device.removePackage(app_id)

# Now process the data and return a number that may or may-not mean anything!

# first we need to find the actual systrace lines in the html output
trace_lines = []
traceStarted = False
for line in open(systrace_output):
    if traceStarted:
        if line.startswith('<!-- END TRACE -->'):
            break
        if '-' + str(pid) in line:
            trace_lines.append(line.strip())
    else:
        if line.startswith('<!-- BEGIN TRACE -->'):
            traceStarted = True
            continue

# only take the middle 50% of the data to remove inconsitencies when starting
# and stopping
size = len(trace_lines)
start = size / 4
end = size - start
trace_lines = trace_lines[start:end]

# collect the deltas for 'performTraversals' which occurs each time the view is
# drawn
deltas = []
last_traversal = 0
for line in trace_lines:
    if 'performTraversals' in line:
        traversal = float(line.split(' ')[3].strip(':'))
        delta = traversal - last_traversal
        if last_traversal != 0:
            deltas.append(delta)
        last_traversal = traversal

# get the delta average for our magic number!
average = sum(deltas) / float(len(deltas))
print "your score is: " + str(average)

