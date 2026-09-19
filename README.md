# Isosurface extraction comparison

## Installation steps
- Install python
- Install dependencies `pip install -r requirements.txt` and `jupyter labextension install @jupyter-widgets/jupyterlab-manager jupyter-matplotlib`
- Launch jupyter-lab `jupyter lab` and open `main.ipynb` file there

## Building the manuscript
- Assemble `article/*.md` into a `.docx` laid out with the journal template:
  `python tools/build_article.py` (see [tools/README.md](tools/README.md) for profiles and options)

## Useful commands
- Install export plugin: `poetry self add poetry-plugin-export`
- Export dependencies into requirements.txt: `poetry export --without-hashes --format requirements.txt --with dev --output requirements.txt`
