"""读取完整原件后保留本机副本；iCloud 下载不能阻塞 HTTP 工作线程。"""
import hashlib
import json
import threading
import time
from pathlib import Path


class RecordUnavailable(OSError):
    pass


class LocalReader:
    def __init__(self, cache=None, timeout=4):
        self.cache = Path(cache or Path.home() / 'Library/Caches/business-analysis-case-viewer')
        self.timeout = timeout
        self.lock = threading.Lock()
        self.pending = {}
        self.slots = threading.BoundedSemaphore(4)

    @staticmethod
    def version(path):
        st = path.stat()
        return [st.st_size, st.st_mtime_ns, st.st_ino]

    def files(self, path):
        key = hashlib.sha256(str(path).encode()).hexdigest()
        return self.cache / (key + '.data'), self.cache / (key + '.json')

    def cached(self, path, version):
        data, meta = self.files(path)
        try:
            info = json.loads(meta.read_text())
            if info['version'] != version:
                return None
            body = data.read_bytes()
            if len(body) == version[0] and hashlib.sha256(body).hexdigest() == info['sha256']:
                return body
        except (OSError, ValueError, KeyError):
            pass
        return None

    def load(self, path, version, pending):
        try:
            # File Provider 有时先返回空内容；完整长度及前后版本一致才接受。
            for attempt in range(3):
                body = path.read_bytes()
                if len(body) == version[0] and self.version(path) == version:
                    pending['body'] = body
                    self.cache.mkdir(parents=True, exist_ok=True)
                    data, meta = self.files(path)
                    data_tmp = data.with_suffix('.tmp')
                    meta_tmp = meta.with_suffix('.tmp')
                    try:
                        data_tmp.write_bytes(body)
                        data_tmp.replace(data)
                        meta_tmp.write_text(json.dumps({'path': str(path), 'version': version,
                            'sha256': hashlib.sha256(body).hexdigest()}))
                        meta_tmp.replace(meta)
                    except OSError:
                        pass  # 缓存写入失败不影响完整原件的读取。
                    return
                if attempt < 2:
                    time.sleep(.1)
            pending['error'] = RecordUnavailable(f'文件尚未完整下载或正在变化：{path.name}')
        except OSError as error:
            pending['error'] = RecordUnavailable(f'文件暂时无法读取：{path.name}（{error.strerror or type(error).__name__}）')
        finally:
            pending['done'].set()
            self.slots.release()
            with self.lock:
                self.pending.pop((path, tuple(version)), None)

    def read(self, path):
        path = Path(path).resolve()
        version = self.version(path)
        body = self.cached(path, version)
        if body is not None:
            return body
        key = (path, tuple(version))
        with self.lock:
            pending = self.pending.get(key)
            if pending is None:
                if not self.slots.acquire(blocking=False):
                    raise RecordUnavailable(f'正在下载其他记录，请稍后重试：{path.name}')
                pending = {'done': threading.Event()}
                self.pending[key] = pending
                threading.Thread(target=self.load, args=(path, version, pending), daemon=True).start()
        if not pending['done'].wait(self.timeout):
            raise RecordUnavailable(f'本地文件未就绪，可能仍在等待 iCloud 下载：{path.name}。稍后点击「重新读取」。')
        if 'error' in pending:
            raise pending['error']
        return pending['body']


READER = LocalReader()


def read_bytes(path):
    return READER.read(path)


def read_text(path):
    return read_bytes(path).decode('utf-8')
