CREATE TABLE settings_new(
			key CHAR(256),
			value CHAR(256),
			id CHAR(256),
			PRIMARY KEY (key, id)
		);
CREATE TABLE shows(
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name CHAR(256),
			feed_name CHAR(256),
			hq BOOLEAN,
			ignore BOOLEAN
		);

