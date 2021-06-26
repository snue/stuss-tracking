#!/bin/bash

mysql -u root -p <<EOF
CREATE DATABASE IF NOT EXISTS besuchertracker;

CREATE TABLE IF NOT EXISTS besuchertracker.stammdaten (
  besucher_id INT,
  kontakt VARCHAR(190),
  status VARCHAR(16),
  zustand VARCHAR(16),
  PRIMARY KEY (besucher_id));

CREATE TABLE IF NOT EXISTS besuchertracker.verlaufsdaten (
  id INT AUTO_INCREMENT,
  zeitstempel DATETIME,
  scanner VARCHAR(16),
  besucher_id INT,
  aktion VARCHAR(16),
  PRIMARY KEY (id));

EOF
