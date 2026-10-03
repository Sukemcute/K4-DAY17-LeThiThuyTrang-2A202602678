"""Build an allowlisted submission archive and verify it in a fresh checkout copy."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = ['README.md','Guide.md','Rubric.md','STEP8.md','REPORT.md',
         'requirements.txt','requirements-live.txt','requirements-live.lock.txt','.gitignore','.env.example']
DIRECTORIES = ['src','data','scripts','results','results-ablation','results-openai-audit','results-openrouter-audit']
ALLOWED_EXTENSIONS = {'.py','.md','.txt','.json','.jsonl'}


def sources():
    files = [ROOT / name for name in FILES if (ROOT / name).is_file()]
    for directory in DIRECTORIES:
        for path in (ROOT / directory).rglob('*'):
            if path.is_file() and path.suffix in ALLOWED_EXTENSIONS and '__pycache__' not in path.parts:
                files.append(path)
    return sorted(set(files))


def verify_no_secrets(files):
    secrets = [value for key,value in os.environ.items() if key.endswith('API_KEY') and len(value) > 12]
    try:
        from dotenv import dotenv_values
        secrets += [value for key,value in dotenv_values(ROOT / '.env').items()
                    if key.endswith('API_KEY') and value and len(value) > 12]
    except ImportError:
        pass
    for path in files:
        text = path.read_text(encoding='utf-8-sig')
        if any(secret in text for secret in secrets):
            raise RuntimeError(f'Secret detected in submission file: {path.relative_to(ROOT)}')
        if path.name == '.env' or any(part in {'state','.venv','.ai-log','.agent','.git'} for part in path.relative_to(ROOT).parts):
            raise RuntimeError('Forbidden path in submission')


def main():
    files = sources()
    verify_no_secrets(files)
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='day17-submission-check-') as temporary:
        checkout = Path(temporary) / ROOT.name
        for path in files:
            target = checkout / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path,target)
        assert not (checkout / '.env').exists() and not (checkout / 'state').exists()
        benchmark = subprocess.run([sys.executable,'-X','utf8','-S','src/benchmark.py','--output-dir','verification-results'],
                                   cwd=checkout,capture_output=True,text=True,encoding='utf-8')
        tests = subprocess.run([sys.executable,'-X','utf8','-m','pytest','src/test_agents.py','-v'],
                               cwd=checkout,capture_output=True,text=True,encoding='utf-8')
        verification = {'clean_copy_without_env_or_state':True,'benchmark_exit_code':benchmark.returncode,
                        'tests_exit_code':tests.returncode,'source_files':len(files),
                        'benchmark_output':benchmark.stdout,'test_output':tests.stdout}
        (output / 'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if benchmark.returncode or tests.returncode:
            print('Fresh-copy verification failed. See dist/verification.json')
            sys.exit(1)
    archive = output / f'{ROOT.name}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as stream:
        for path in files:
            stream.write(path, (Path(ROOT.name) / path.relative_to(ROOT)).as_posix())
        stream.write(output / 'verification.json', f'{ROOT.name}/verification.json')
    print('Fresh-copy benchmark and tests passed.')
    print('Archive:',archive)
    print('Files:',len(files)+1)


if __name__ == '__main__':
    main()
