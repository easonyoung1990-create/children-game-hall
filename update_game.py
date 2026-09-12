"""Replace a prepared game without changing its stable URL; no remote deployment."""
from pathlib import Path
from html.parser import HTMLParser
import argparse,hashlib,json,os,re,shutil,datetime

class Resources(HTMLParser):
    def __init__(self): super().__init__(); self.refs=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ('script','img','audio','video','source','iframe','link'):
            value=a.get('src',a.get('href',''))
            if value and not value.startswith(('data:','#')):self.refs.append(value)

def update(root,game,source,version):
    manifest_path=root/'games.json'; manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    item=next(x for x in manifest['games'] if x['id']==game)
    target=root/item['path'];raw=source.read_bytes();text=raw.decode('utf-8')
    if not re.search(r'<html\b',text,re.I):raise ValueError('需要完整 HTML 游戏文件')
    parser=Resources();parser.feed(text)
    for ref in parser.refs:
        if ref.startswith(('http:','https:','//')):raise ValueError('游戏仍有外部资源，请先一并打包: '+ref)
        if not (target.parent/ref.split('?')[0].split('#')[0]).is_file():raise ValueError('缺少配套资源: '+ref)
    # The two existing families must preserve their own storage identities.
    prefix={'kenton':'mcv7-accounts','eddey':'mcv82-accounts'}.get(game)
    if prefix and prefix not in text:raise ValueError('存档标识变化，请先验证迁移方案')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=root.parent/'rollback'/game/stamp;backup.mkdir(parents=True)
    shutil.copyfile(target,backup/'index.html');shutil.copyfile(manifest_path,backup/'games.json')
    tmp=target.with_suffix('.pending');tmp.write_bytes(raw);os.replace(tmp,target)
    item.update(version=version,sha256=hashlib.sha256(raw).hexdigest(),source='Updated via update_game.py')
    manifest['deployment_status']='not_deployed';manifest['prepared_at']=stamp
    mt=manifest_path.with_suffix('.pending')
    mt.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(mt,manifest_path)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256']
    print('本地更新完成。固定路径：'+item['path']+'；尚未发布。')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('game',choices=['kenton','eddey','backrooms']);p.add_argument('source',type=Path);p.add_argument('--version',required=True);p.add_argument('--site',type=Path,default=Path(__file__).parent/'site');a=p.parse_args()
    update(a.site,a.game,a.source,a.version)
