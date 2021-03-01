CREATE TABLE File
(
  hash bytea NOT NULL,
  data bytea,
  type text  NOT NULL,
  PRIMARY KEY (hash),
  CONSTRAINT Check_Valid_Type
    CHECK (type ~ '^\w+\/[-+.\w]+$'),
  CONSTRAINT Check_Hash_Matches_Data
    CHECK (hash = sha256(data))
);

CREATE TABLE NetworkSource
(
  ip_address inet NOT NULL,
  PRIMARY KEY (ip_address)
);

CREATE TABLE Session
(
  id              serial    NOT NULL,
  attack_src      inet      NOT NULL,
  protocol        text      NOT NULL,
  src_port        int       NOT NULL,
  dst_ip          inet      NOT NULL,
  dst_port        int       NOT NULL,
  start_timestamp timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  end_timestamp   timestamp,
  PRIMARY KEY (id),
  UNIQUE (id, protocol),
  CONSTRAINT FK_NetworkSource_TO_Session
    FOREIGN KEY (attack_src)
    REFERENCES NetworkSource (ip_address),
  CONSTRAINT Check_Protocol_Valid
    CHECK (protocol IN ('SSH')),
  CONSTRAINT Check_Ports_In_Range
    CHECK (src_port BETWEEN 0 AND 65535 AND dst_port BETWEEN 0 AND 65535),
  CONSTRAINT Check_End_Timestamp_Is_After_Start
    CHECK (end_timestamp IS NOT NULL AND start_timestamp <= end_timestamp)
);

CREATE TABLE SSHSession
(
  term       text NOT NULL,
  session_id int  NOT NULL,
  protocol   text NOT NULL DEFAULT 'SSH',
  CONSTRAINT FK_Session_TO_SSHSession
    FOREIGN KEY (session_id, protocol)
    REFERENCES Session (id, protocol),
  CONSTRAINT Check_Correct_Protocol
    CHECK (protocol = 'SSH')
);

CREATE TABLE EventType
(
  name text NOT NULL,
  PRIMARY KEY (name),
  CONSTRAINT Check_Valid_Name
    CHECK (length(name) > 0)
);

INSERT INTO EventType VALUES
  ('command'),
  ('download'),
  ('login_attempt');

CREATE TABLE Event
(
  id         serial    NOT NULL,
  session_id int       NOT NULL,
  type       text      NOT NULL,
  timestamp  timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE (id, type),
  CONSTRAINT FK_Session_TO_Event
    FOREIGN KEY (session_id)
    REFERENCES Session (id),
  CONSTRAINT FK_EventType_TO_Event
    FOREIGN KEY (type)
    REFERENCES EventType (name)
);

CREATE TABLE Command
(
  event_id   int   NOT NULL,
  event_type text  NOT NULL DEFAULT 'command',
  input      text  NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_Command_TO_Event
    FOREIGN KEY (event_id, event_type)
    REFERENCES Event (id, type),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'command')
);

CREATE TABLE Download
(
  event_id   int   NOT NULL,
  event_type text  NOT NULL DEFAULT 'download',
  hash       bytea NOT NULL,
  src        inet  NOT NULL,
  url        text,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_File_TO_Download
    FOREIGN KEY (hash)
    REFERENCES File (hash),
  CONSTRAINT FK_NetworkSource_TO_Download
    FOREIGN KEY (src)
    REFERENCES NetworkSource (ip_address),
  CONSTRAINT FK_Download_TO_Event
    FOREIGN KEY (event_id, event_type)
    REFERENCES Event (id, type),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'download'),
  CONSTRAINT Check_Valid_URL
    CHECK (url ~ '^(([^:/?#]+):)?(//([^/?#]*))?([^?#]*)(\?([^#]*))?(#(.*))?')
);

CREATE TABLE LoginAttempt
(
  event_id   int  NOT NULL,
  event_type text NOT NULL DEFAULT 'login_attempt',
  username   text NOT NULL,
  password   text NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_LoginAttempt_TO_Event
    FOREIGN KEY (event_id, event_type)
    REFERENCES Event (id, type),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'login_attempt')
);


      