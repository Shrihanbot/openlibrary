import py.test
import os.path
import web
import simplejson
import time
import urllib

from openlibrary.coverstore import config, disk, schema, code, utils, archive
import _setup

def setup_module(mod):
    _setup.setup_module(mod, db=True)
    mod.app = code.app
    
def teardown_module(mod):
    _setup.teardown_module(mod)

class TestWebapp:
    def setup_class(self):
        db.delete('cover', where='1=1')
        self.browser = app.browser()
        
    def jsonget(self, path):
        self.browser.open(path)
        return simplejson.loads(self.browser.data)

    def upload(self, olid, path):
        """Uploads an image in static dir"""
        b = self.browser
        
        path = os.path.join(static_dir, path)
        content_type, data = utils.urlencode({'olid': olid, 'file': open(path), 'failure_url': '/failed'}) 
        b.open('/b/upload', data, {'Content-Type': content_type})
        return self.jsonget('/b/olid/%s.json' % olid)['id']
        
    def delete(self, id, redirect_url=None):
        b = self.browser
        
        params = {'id': id}
        if redirect_url:
            params['redirect_url'] = redirect_url
        b.open('/b/delete', urllib.urlencode(params))
        return b.data
        
    def test_touch(self):    
        b = self.browser

        id1 = self.upload('OL1M', 'logos/logo-en.png')
        time.sleep(1)
        id2 = self.upload('OL1M', 'logos/logo-it.png')
        
        assert id1 < id2

        assert b.open('/b/olid/OL1M.jpg').read() == open(static_dir + '/logos/logo-it.png').read()

        b.open('/b/touch', urllib.urlencode({'id': id1}))
        assert b.open('/b/olid/OL1M.jpg').read() == open(static_dir + '/logos/logo-en.png').read()

    def test_delete(self):
        b = self.browser
        
        id1 = self.upload('OL1M', 'logos/logo-en.png')
        data = self.delete(id1)
        assert data == 'cover has been deleted successfully.'
    
    def test_get(self):
        assert app.request('/').status == "200 OK"

    def test_upload(self):
        b = self.browser

        path = os.path.join(static_dir, 'logos/logo-en.png')
        content_type, data = utils.urlencode({'olid': 'OL1234M', 'file': open(path), 'failure_url': '/failed'}) 
        b.open('/b/upload', data, {'Content-Type': content_type})

        assert b.status == 200
        assert b.path == '/'

        b.open('/b/olid/OL1234M.json')

        response = b.open('/b/olid/OL1234M.jpg')
        assert b.status == 200
        assert response.info().getheader('Content-Type') == 'image/jpeg'
        assert b.data == open(path).read()

        b.open('/b/olid/OL1234M-S.jpg')
        assert b.status == 200

        b.open('/b/olid/OL1234M-M.jpg')
        assert b.status == 200

        b.open('/b/olid/OL1234M-L.jpg')
        assert b.status == 200
        
    def test_archive_status(self):
        id = self.upload('OL1M', 'logos/logo-en.png')
        d = self.jsonget('/b/id/%d.json' % id)
        assert d['archived'] == False
        assert d['deleted'] == False

    def test_archive(self):
        b = self.browser
        
        f1 = web.storage(olid='OL1M', filename='logos/logo-en.png')
        f2 = web.storage(olid='OL2M', filename='logos/logo-it.png')
        files = [f1, f2]
        
        for f in files:
            f.id = self.upload(f.olid, f.filename)
            f.path = os.path.join(static_dir, f.filename)
            assert b.open('/b/id/%d.jpg' % f.id).read() == open(f.path).read()
        
        archive.archive()
        
        for f in files:
            d = self.jsonget('/b/id/%d.json' % f.id)
            print f.id, d
            assert 'tar:' in d['filename']
            assert b.open('/b/id/%d.jpg' % f.id).read() == open(f.path).read()
