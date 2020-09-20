--
-- PostgreSQL database dump
--

-- Dumped from database version 12.4
-- Dumped by pg_dump version 12.4

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
    msg text,
    poemable boolean DEFAULT false NOT NULL,
    ignore_err boolean DEFAULT true NOT NULL,
    no_blue boolean DEFAULT false NOT NULL,
    no_service boolean DEFAULT false NOT NULL,
    no_welcome boolean DEFAULT false NOT NULL,
    no_new_member boolean DEFAULT false NOT NULL,
    available boolean DEFAULT true NOT NULL,
    "except" character varying(500) DEFAULT 'W10='::character varying NOT NULL,
    previous_msg integer
);


ALTER TABLE public.welcome_msg OWNER TO postgres;

--
-- Name: welcome_msg2; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.welcome_msg2 (
    group_id bigint NOT NULL,
    available boolean DEFAULT true NOT NULL,
    msg text,
    settings json DEFAULT '{"poemable": false,"ignore_err": false, "no_blue": false, "no_service": false, "no_welcome": false, "no_new_member": false, "except": []}'::json NOT NULL,
    previous_msg integer
);


ALTER TABLE public.welcome_msg2 OWNER TO postgres;

--
-- Name: welcome_msg2 welcome_msg2_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.welcome_msg2
    ADD CONSTRAINT welcome_msg2_pk PRIMARY KEY (group_id);


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

