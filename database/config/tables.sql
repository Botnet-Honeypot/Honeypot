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
    CHECK (protocol IN ('ssh')),
  CONSTRAINT Check_Ports_In_Range
    CHECK (src_port BETWEEN 0 AND 65535 AND dst_port BETWEEN 0 AND 65535),
  CONSTRAINT Check_End_Timestamp_Is_After_Start
    CHECK (CASE WHEN end_timestamp IS NOT NULL THEN start_timestamp <= end_timestamp else TRUE END)
);

CREATE TABLE SSHSession
(
  session_id          int    NOT NULL,
  session_protocol    text   NOT NULL DEFAULT 'ssh',
  ssh_version         text   NOT NULL,
  PRIMARY KEY (session_id),
  CONSTRAINT FK_SSHSession_TO_Session
    FOREIGN KEY (session_id, session_protocol)
    REFERENCES Session (id, protocol),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
);

CREATE TABLE EventType
(
  name text NOT NULL,
  PRIMARY KEY (name),
  CONSTRAINT Check_Valid_Name
    CHECK (length(name) > 0)
);

INSERT INTO EventType VALUES
  ('pty_request'),
  ('env_request'),
  ('direct_tcpip_request'),
  ('x_eleven_request'),
  ('port_forward_request'),
  ('command'),
  ('ssh_channel_output'),
  ('download'),
  ('login_attempt');

CREATE TABLE Event
(
  id               serial    NOT NULL,
  session_id       int       NOT NULL,
  session_protocol text      NOT NULL,
  type             text      NOT NULL,
  timestamp        timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE (id, type),
  UNIQUE (id, type, session_protocol),
  CONSTRAINT FK_Session_TO_Event
    FOREIGN KEY (session_id, session_protocol)
    REFERENCES Session (id, protocol),
  CONSTRAINT FK_EventType_TO_Event
    FOREIGN KEY (type)
    REFERENCES EventType (name)
);

CREATE TABLE PTYRequest
(
  event_id            int   NOT NULL,
  event_type          text  NOT NULL DEFAULT 'pty_request',
  session_protocol    text  NOT NULL DEFAULT 'ssh',
  term                text  NOT NULL,
  term_width_cols     int   NOT NULL,
  term_height_rows    int   NOT NULL,
  term_width_pixels   int   NOT NULL,
  term_height_pixels  int   NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_PTYRequest_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'pty_request'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
);

CREATE TABLE EnvRequest
(
  event_id            int   NOT NULL,
  event_type          text  NOT NULL DEFAULT 'env_request',
  session_protocol    text  NOT NULL DEFAULT 'ssh',
  channel_id          int   NOT NULL,
  name                text  NOT NULL,
  value               text  NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_EnvRequest_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'env_request'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
);

CREATE TABLE DirectTCPIPRequest
(
  event_id            int   NOT NULL,
  event_type          text  NOT NULL DEFAULT 'direct_tcpip_request',
  session_protocol    text  NOT NULL DEFAULT 'ssh',
  channel_id          int   NOT NULL,
  origin_ip           inet  NOT NULL,
  origin_port         int   NOT NULL,
  destination         text  NOT NULL,
  destination_port    int   NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_DirectTCPIPRequest_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'direct_tcpip_request'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
);

CREATE TABLE XElevenRequest
(
  event_id            int     NOT NULL,
  event_type          text    NOT NULL DEFAULT 'x_eleven_request',
  session_protocol    text    NOT NULL DEFAULT 'ssh',
  channel_id          int     NOT NULL,
  single_connection   boolean NOT NULL,
  auth_protocol       text    NOT NULL,
  auth_cookie         bytea   NOT NULL,
  screen_number       int     NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_XElevenRequest_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'x_eleven_request'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
);

CREATE TABLE PortForwardRequest
(
  event_id            int     NOT NULL,
  event_type          text    NOT NULL DEFAULT 'port_forward_request',
  session_protocol    text    NOT NULL DEFAULT 'ssh',
  address             text    NOT NULL,
  port                int     NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_PortForwardRequest_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'port_forward_request'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
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

CREATE TABLE SSHChannelOutput
(
  event_id           int     NOT NULL,
  event_type         text    NOT NULL DEFAULT 'ssh_channel_output',
  session_protocol   text    NOT NULL DEFAULT 'ssh',
  data               bytea   NOT NULL,
  channel            int     NOT NULL,
  PRIMARY KEY (event_id, event_type),
  CONSTRAINT FK_Command_TO_Event
    FOREIGN KEY (event_id, event_type, session_protocol)
    REFERENCES Event (id, type, session_protocol),
  CONSTRAINT Check_Correct_Type
    CHECK (event_type = 'ssh_channel_output'),
  CONSTRAINT Check_Correct_Protocol
    CHECK (session_protocol = 'ssh')
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


      