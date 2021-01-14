VERSION=0.0.1_alpha
PREFIX=/usr/local
MAN_LOC=share/man/man1
BIN_LOC=bin
BIN=sdss
MAN_PAGE=sdss.1

install: $(BIN) $(MAN_PAGE)
	mkdir -p $(PREFIX)/$(BIN_LOC)
	cp -f ./$(BIN) $(PREFIX)/$(BIN_LOC)
	chmod 0755 $(PREFIX)/$(BIN_LOC)/$(BIN)
	mkdir -p $(PREFIX)/$(MAN_LOC)
	cp -f ./$(MAN_PAGE) $(PREFIX)/$(MAN_LOC)
	chmod 0644 $(PREFIX)/$(MAN_LOC)/$(MAN_PAGE)
	sed -i 's/VERSION/$(VERSION)/g' $(PREFIX)/$(MAN_LOC)/$(MAN_PAGE)
	mandb
