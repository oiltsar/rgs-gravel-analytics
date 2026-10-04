.PHONY: all setup extract transform load notebook dashboard presentation clean

all: extract transform load notebook dashboard

setup:            ## поставить окружение
	uv sync

extract:          ## скачать сырые протоколы с gravelseries.ru
	uv run python -m gravel.extract

transform:        ## очистка + сведение гонщиков -> parquet
	uv run python -m gravel.transform

load:             ## parquet -> DuckDB + SQL-витрины
	uv run python -m gravel.load

notebook:         ## выполнить аналитический ноутбук (графики -> reports/figures)
	uv run python notebooks/build_notebook.py
	uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb

dashboard:        ## собрать данные для интерактивного дашборда
	uv run python -m gravel.dashboard_data

clean:
	rm -rf data/processed/* data/gravel.duckdb

presentation:     ## PDF-презентация из presentation/slides.html (нужен Google Chrome)
	"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --no-pdf-header-footer \
		--virtual-time-budget=8000 --print-to-pdf="$(CURDIR)/presentation/Presentation_RGS.pdf" "file://$(CURDIR)/presentation/slides.html"
