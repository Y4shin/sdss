VERSION=0.0.1_alpha
PREFIX=/usr/local
MAN_LOC=share/man
BIN_LOC=bin
BIN=sdss
MAN_PAGE=sdss

install: $(BIN) $(MAN_PAGE).1
	mkdir -p $(PREFIX)/$(BIN_LOC)
	cp -f ./$(BIN) $(PREFIX)/$(BIN_LOC)
	chmod 0755 $(PREFIX)/$(BIN_LOC)/$(BIN)
	sed -i 's/CUR_VERSION/$(VERSION)/g' $(PREFIX)/$(BIN_LOC)/$(BIN)
	mkdir -p $(PREFIX)/$(MAN_LOC)/man1
	cp -f ./$(MAN_PAGE).1 $(PREFIX)/$(MAN_LOC)/man1
	chmod 0644 $(PREFIX)/$(MAN_LOC)/man1/$(MAN_PAGE).1
	sed -i 's/CUR_VERSION/$(VERSION)/g' $(PREFIX)/$(MAN_LOC)/man1/$(MAN_PAGE).1
	mkdir -p $(PREFIX)/$(MAN_LOC)/man5
	cp -f ./$(MAN_PAGE).5 $(PREFIX)/$(MAN_LOC)/man5
	chmod 0644 $(PREFIX)/$(MAN_LOC)/man5/$(MAN_PAGE).5
	sed -i 's/CUR_VERSION/$(VERSION)/g' $(PREFIX)/$(MAN_LOC)/man5/$(MAN_PAGE).5
	mandb
