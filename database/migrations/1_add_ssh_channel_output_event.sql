BEGIN;

INSERT INTO EventType VALUES
  ('ssh_channel_output');

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

COMMIT;