"""Execute the actual service stop/close bodies against a retained bound-service boundary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
service_path = root / 'android/applock/src/main/java/despia/ext/applock/LockDnsService.java'
extension_path = service_path.with_name('AppLockExtension.java')
service = service_path.read_text()
extension = extension_path.read_text()
args.output.mkdir(parents=True, exist_ok=False)
close = method(service, 'private void close(Session owner)')
if 'static void stop(Context context)' in service:
    stop = method(service, 'static void stop(Context context)')
    extraction = 'Actual production LockDnsService.stop and close methods'
else:
    statement = 'context.stopService(new Intent(context, LockDnsService.class));'
    assert statement in extension
    stop = 'static void stop(Context context) { ' + statement + ' }'
    extraction = 'Baseline releaseAll stop statement wrapped only for test entry; actual close method'
java = r'''
import java.io.*;
import java.net.*;
public final class LockDnsService {
 static LockDnsService active;
 final Object sessions=new Object();
 Session session;
 static final int STOP_FOREGROUND_REMOVE=1;
 boolean notification=true;
 static int failures,checks;
 static final class Tunnel implements Closeable {boolean closed;int closes;public void close() throws IOException {closed=true;closes++;}}
 static final class Session {boolean running=true;Socket upstream=new Socket();Tunnel tunnel=new Tunnel();String lastError;}
 static final class Intent {Intent(Context context,Class<?> service){}}
 static final class Context {
  final LockDnsService service;boolean started=true;final boolean bound=true;int stops;
  Context(LockDnsService service){this.service=service;}
  boolean stopService(Intent intent){stops++;started=false;return true;}
 }
 static final class android {static final class util {static final class Log {static void w(String tag,String message){throw new AssertionError(message);}}}}
 void record(String kind,String detail){}
 void stopForeground(int flags){notification=false;}
 STOP_METHOD
 CLOSE_METHOD
 static void check(boolean truth,String label){checks++;if(truth)System.out.println("PASS "+label);else{failures++;System.out.println("FAIL "+label);}}
 static LockDnsService running(){LockDnsService service=new LockDnsService();service.session=new Session();active=service;return service;}
 public static void main(String[] args){
  LockDnsService service=running();Session owner=service.session;Socket upstream=owner.upstream;Context context=new Context(service);
  stop(context);
  check(!owner.running&&owner.tunnel.closed&&upstream.isClosed(),"bound VPN stop closes tunnel and resolver without onDestroy");
  check(service.session==null&&active==null&&!service.notification,"native running state and notification clear immediately");
  check(context.stops==1&&!context.started&&context.bound,"stop start-request while preserving OS-owned binding");
  stop(context);check(owner.tunnel.closes==1&&context.stops==2,"repeat stop is idempotent and does not recreate service");
  service=running();owner=service.session;service.close(owner);Session replacement=new Session();service.session=replacement;active=service;service.notification=true;service.close(owner);
  check(service.session==replacement&&active==service&&replacement.running&&!replacement.tunnel.closed&&service.notification,"old reader cleanup cannot close replacement session");
  service=running();owner=service.session;owner.running=false;context=new Context(service);stop(context);
  check(owner.tunnel.closed&&service.session==null&&active==null,"partially stopped session resources still close");
  System.out.println("CHECKS "+checks+" FAILURES "+failures);if(failures!=0)System.exit(1);
 }
}
'''.replace('STOP_METHOD', stop).replace('CLOSE_METHOD', close)
java_path = args.output / 'LockDnsService.java'
java_path.write_text(java)
(args.output / 'tmp').mkdir()
classes = args.output / 'classes'
classes.mkdir()
jdk = Path('/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin')
env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'TMPDIR': str(args.output / 'tmp'), 'LANG': 'en_US.UTF-8'}
if 'HOME' in os.environ:
    env['HOME'] = os.environ['HOME']
compile_command = [str(jdk / 'javac'), '-J-Xmx96m', '-J-Djava.io.tmpdir=' + str(args.output / 'tmp'), '--release', '17', '-d', str(classes), str(java_path)]
run_command = [str(jdk / 'java'), '-Xmx64m', '-Djava.io.tmpdir=' + str(args.output / 'tmp'), '-cp', str(classes), 'LockDnsService']
commands = []
for name, argv in [('compile', compile_command), ('run', run_command)]:
    with (args.output / (name + '.log')).open('w') as log:
        completed = subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=25)
    commands.append({'phase': name, 'argv': argv, 'exit': completed.returncode})
    if completed.returncode:
        break
route_delegates = 'cancelVpnRequest(); LockDnsService.stop(context.app());' in extension
release_delegates = 'LockDnsService.stop(context); LockAccessibilityService.refreshCurrent();' in extension
receipt = {'extraction': extraction, 'framework_boundary': 'Controlled bound Context does not invoke onDestroy on stopService, matching retained API37 service dump. Not an Android OS test.', 'commands': commands, 'route_delegates': route_delegates, 'release_delegates': release_delegates, 'hashes': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in [service_path, extension_path, Path(__file__), java_path]}, 'exit': commands[-1]['exit'] or (0 if route_delegates and release_delegates else 1)}
(args.output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print((args.output / (commands[-1]['phase'] + '.log')).read_text())
print('route_delegates', route_delegates, 'release_delegates', release_delegates)
raise SystemExit(receipt['exit'])
