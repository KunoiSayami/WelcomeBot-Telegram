--
-- PostgreSQL database dump
--

-- Dumped from database version 14.3
-- Dumped by pg_dump version 14.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: poem; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.poem (
    string text
);


ALTER TABLE public.poem OWNER TO postgres;

--
-- Name: welcome_msg; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.welcome_msg (
    group_id bigint NOT NULL,
    available boolean,
    msg text,
    flags bytea,
    "except" bigint[] DEFAULT ARRAY[]::bigint[] NOT NULL,
    previous_msg_id integer
);


ALTER TABLE public.welcome_msg OWNER TO postgres;

--
-- Name: welcome_msg welcome_msg_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.welcome_msg
    ADD CONSTRAINT welcome_msg_pk PRIMARY KEY (group_id);


--
-- Name: poem_string_uindex; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX poem_string_uindex ON public.poem USING btree (string);


--
-- PostgreSQL database dump complete
--

