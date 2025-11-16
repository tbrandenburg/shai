import json
import time
import traceback
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

notebook_dir = Path('notebooks')
results = []
for nb_path in sorted(notebook_dir.glob('day*.ipynb')):
    start = time.time()
    status = 'passed'
    notes = []
    print(f'Executing {nb_path.name} ...', flush=True)
    try:
        nb = nbformat.read(nb_path, as_version=4)
        client = NotebookClient(
            nb,
            timeout=600,
            kernel_name='python3',
            resources={'metadata': {'path': str(nb_path.parent)}},
            allow_errors=False,
        )
        client.execute()
        nbformat.write(nb, nb_path)
    except CellExecutionError as exc:
        status = 'failed'
        notes.append(f'CellExecutionError: {exc}')
        print(f'Execution failed for {nb_path.name}: {exc}', flush=True)
    except Exception as exc:
        status = 'error'
        notes.append(f'Exception: {exc}')
        traceback.print_exc()
    duration = time.time() - start
    results.append(
        {
            'notebook': nb_path.name,
            'status': status,
            'duration_sec': round(duration, 2),
            'notes': notes,
        }
    )

summary_path = Path('notebook_validation_results.json')
summary_path.write_text(json.dumps({'results': results}, indent=2))
print('Validation summary written to', summary_path)
for entry in results:
    print(
        f"{entry['notebook']}: {entry['status']} ({entry['duration_sec']}s)",
        flush=True,
    )
    for note in entry['notes']:
        print('  -', note, flush=True)
