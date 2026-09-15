import hashlib
def check(root, subjects):
    for subject in subjects:
        path = (root / subject['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != subject['sha256']:
            return False
    return True
