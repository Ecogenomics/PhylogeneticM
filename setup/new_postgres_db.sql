CREATE TABLE databases (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
);

CREATE table user_types (
    id integer PRIMARY KEY, 
    name text UNIQUE NOT NULL
);

CREATE TABLE users (
    id serial PRIMARY KEY,
    username text UNIQUE NOT NULL,
    password text NOT NULL,
    type_id integer NOT NULL,
    FOREIGN KEY (type_id) REFERENCES user_types(id) ON UPDATE CASCADE
);

CREATE TABLE genome_sources (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
);

CREATE TABLE genomes (
    id serial PRIMARY KEY,
    tree_id text UNIQUE NOT NULL,
    name text NOT NULL,
    description text,
    metadata xml,
    genomic_fasta oid,
    owner_id integer NOT NULL,
    genome_source_id integer NOT NULL,
    id_at_source text NOT NULL,
    UNIQUE (genome_source_id, id_at_source),
    FOREIGN KEY (genome_source_id) REFERENCES genome_sources(id) ON UPDATE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON UPDATE CASCADE
);

CREATE TABLE markers (
    id serial PRIMARY KEY,
    database_specific_id text NOT NULL,
    name text NOT NULL,
    size integer,
    timestamp timestamp NOT NULL,
    database_id integer NOT NULL,
    hmm oid,
    UNIQUE (database_specific_id, timestamp, database_id),   
    FOREIGN KEY (database_id) REFERENCES databases(id) ON UPDATE CASCADE
);

CREATE TABLE aligned_markers (
    genome_id integer NOT NULL,
    marker_id integer NOT NULL,
    dna boolean NOT NULL,
    sequence text,
    PRIMARY KEY (genome_id, marker_id, dna),
    FOREIGN KEY (marker_id) REFERENCES markers(id) ON UPDATE CASCADE,
    FOREIGN KEY (genome_id) REFERENCES genomes(id) ON UPDATE CASCADE
);

CREATE TABLE genome_lists (
    id serial PRIMARY KEY,
    name text NOT NULL,
    description text,
    owner_id integer NOT NULL,
    private bool NOT NULL DEFAULT TRUE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON UPDATE CASCADE
);

CREATE TABLE genome_list_contents (
    list_id integer NOT NULL,
    genome_id integer NOT NULL,
    PRIMARY KEY (list_id, genome_id),
    FOREIGN KEY (genome_id) REFERENCES genomes(id) ON UPDATE CASCADE,
    FOREIGN KEY (list_id) REFERENCES genome_lists(id) ON UPDATE CASCADE
);

CREATE TABLE marker_sets (
    id serial PRIMARY KEY,
    name text NOT NULL,
    description text,
    owner_id integer NOT NULL,
    private bool NOT NULL DEFAULT TRUE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON UPDATE CASCADE
);

CREATE TABLE marker_set_contents (
    set_id integer NOT NULL,
    marker_id integer NOT NULL,
    PRIMARY KEY (set_id, marker_id),
    FOREIGN KEY (marker_id) REFERENCES markers(id) ON UPDATE CASCADE,
    FOREIGN KEY (set_id) REFERENCES marker_sets(id) ON UPDATE CASCADE
);


INSERT INTO user_types VALUES (0, 'root');
INSERT INTO user_types VALUES (1, 'admin');
INSERT INTO user_types VALUES (2, 'user');
INSERT INTO users (username, password, type_id) VALUES ('root', '', 0);
INSERT INTO genome_sources (name) VALUES ('user');
INSERT INTO genome_sources (name) VALUES ('IMG');
INSERT INTO genome_sources (name) VALUES ('NCBI');
