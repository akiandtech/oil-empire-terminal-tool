ACTIVATE = . venv/Scripts/activate

.PHONY: install run build

install:
	$(ACTIVATE) && uv pip install -r requirements-dev.txt

run:
	$(ACTIVATE) && python main.py

build:
	$(ACTIVATE) && pyinstaller --onefile --name oil-empire-tool --collect-all textual main.py

deploy: build
	mkdir -p /c/tools/bin
	cp -f dist/oil-empire-tool.exe /c/tools/bin/oil-empire-tool.exe
