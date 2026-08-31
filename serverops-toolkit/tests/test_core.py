import json,os,tempfile,unittest
from serverops.config import deep_merge,load_config
from serverops.port_checks import check_tcp
from serverops.report import summarize
from serverops.common import CheckResult,OK,WARN
from serverops.ip_scan import scan_ip_references

class CoreTests(unittest.TestCase):
    def test_merge(self): self.assertEqual(deep_merge({'a':{'b':1,'c':2}},{'a':{'b':3}})['a'],{'b':3,'c':2})
    def test_config(self):
        with tempfile.NamedTemporaryFile('w',delete=False) as fh: json.dump({'services':['sshd']},fh); path=fh.name
        try: self.assertEqual(load_config(path)['services'],['sshd'])
        finally: os.unlink(path)
    def test_report(self): self.assertEqual(summarize([CheckResult('x','a',OK,'ok'),CheckResult('x','b',WARN,'warn')])['total'],2)
    def test_port(self): self.assertIn(check_tcp('127.0.0.1',1,0.05).status,{'OK','FAIL'})
    def test_ip_scan(self):
        with tempfile.TemporaryDirectory() as td:
            p=os.path.join(td,'app.conf'); open(p,'w').write('backend=10.112.58.218\n')
            r=scan_ip_references('10.112.58.218',{'ip_scan_roots':[td],'ip_scan_excludes':[],'ip_scan_max_file_bytes':10000})
            self.assertTrue(any(x.name==p for x in r))

if __name__=='__main__': unittest.main()
