-- 股票历史行情相关表：不复权和后复权

-- Table: public.股票历史行情_不复权

-- DROP TABLE IF EXISTS public."股票历史行情_不复权";

CREATE TABLE IF NOT EXISTS public."股票历史行情_不复权"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "开盘" double precision,
    "收盘" double precision,
    "最高" double precision,
    "最低" double precision,
    "成交量" numeric(38,0),
    "成交额" numeric(38,0),
    "振幅" double precision,
    "涨跌幅" double precision,
    "涨跌额" double precision,
    "换手率" double precision,
    CONSTRAINT "股票历史行情_不复权_pkey" PRIMARY KEY ("股票代码", "日期")
) PARTITION BY HASH ("股票代码");

ALTER TABLE IF EXISTS public."股票历史行情_不复权"
    OWNER to postgres;
-- Index: idx_no_adjust_date

-- DROP INDEX IF EXISTS public.idx_no_adjust_date;

CREATE INDEX IF NOT EXISTS idx_no_adjust_date
    ON public."股票历史行情_不复权" USING btree
    ("日期" ASC NULLS LAST)
;

-- Partitions SQL

CREATE TABLE public."股票历史行情_不复权_0" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 0)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_0"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_1" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 1)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_1"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_2" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 2)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_2"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_3" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 3)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_3"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_4" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 4)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_4"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_5" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 5)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_5"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_6" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 6)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_6"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_7" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 7)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_7"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_8" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 8)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_8"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_9" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 9)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_9"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_10" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 10)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_10"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_11" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 11)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_11"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_12" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 12)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_12"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_13" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 13)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_13"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_14" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 14)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_14"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_不复权_15" PARTITION OF public."股票历史行情_不复权"
    FOR VALUES WITH (modulus 16, remainder 15)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_不复权_15"
    OWNER to postgres;


-- Table: public.股票历史行情_后复权

-- DROP TABLE IF EXISTS public."股票历史行情_后复权";

CREATE TABLE IF NOT EXISTS public."股票历史行情_后复权"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "开盘" double precision,
    "收盘" double precision,
    "最高" double precision,
    "最低" double precision,
    "成交量" numeric(38,0),
    "成交额" numeric(38,0),
    "振幅" double precision,
    "涨跌幅" double precision,
    "涨跌额" double precision,
    "换手率" double precision,
    CONSTRAINT "股票历史行情_后复权_pkey" PRIMARY KEY ("股票代码", "日期")
) PARTITION BY HASH ("股票代码");

ALTER TABLE IF EXISTS public."股票历史行情_后复权"
    OWNER to postgres;
-- Index: idx_hfq_date

-- DROP INDEX IF EXISTS public.idx_hfq_date;

CREATE INDEX IF NOT EXISTS idx_hfq_date
    ON public."股票历史行情_后复权" USING btree
    ("日期" ASC NULLS LAST)
;

-- Partitions SQL

CREATE TABLE public."股票历史行情_后复权_0" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 0)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_0"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_1" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 1)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_1"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_2" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 2)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_2"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_3" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 3)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_3"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_4" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 4)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_4"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_5" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 5)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_5"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_6" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 6)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_6"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_7" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 7)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_7"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_8" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 8)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_8"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_9" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 9)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_9"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_10" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 10)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_10"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_11" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 11)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_11"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_12" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 12)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_12"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_13" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 13)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_13"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_14" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 14)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_14"
    OWNER to postgres;
CREATE TABLE public."股票历史行情_后复权_15" PARTITION OF public."股票历史行情_后复权"
    FOR VALUES WITH (modulus 16, remainder 15)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_后复权_15"
    OWNER to postgres;