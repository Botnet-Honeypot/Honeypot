CREATE TABLE AttackSource
(
  ip_address inet NOT NULL,
  country    text NOT NULL,
  city       text NOT NULL,
  PRIMARY KEY (ip_address)
);

CREATE TABLE LoginAttempt
(
  id             serial    NOT NULL,
  session_id     serial    NOT NULL,
  username       text      NOT NULL,
  password       text      NOT NULL,
  date_timestamp timestamp NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE Session
(
  id              serial    NOT NULL,
  attack_source   inet      NOT NULL,
  protocol        text      NOT NULL,
  src_port        int       NOT NULL,
  dest_ip         inet      NOT NULL,
  dest_port       int       NOT NULL,
  start_timestamp timestamp NOT NULL,
  end_timestamp   timestamp NOT NULL,
  PRIMARY KEY (id)
);

ALTER TABLE LoginAttempt
  ADD CONSTRAINT FK_Session_TO_LoginAttempt
    FOREIGN KEY (session_id)
    REFERENCES Session (id);

ALTER TABLE Session
  ADD CONSTRAINT FK_AttackSource_TO_Session
    FOREIGN KEY (attack_source)
    REFERENCES AttackSource (ip_address);

      