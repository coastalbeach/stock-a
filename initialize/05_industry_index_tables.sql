-- 行业和指数相关表：行业历史行情、指数历史行情

-- Table: public.行业历史行情

-- DROP TABLE IF EXISTS public."行业历史行情";

CREATE TABLE IF NOT EXISTS public."行业历史行情"
(
    "行业名称" character varying(100) COLLATE pg_catalog."default" NOT NULL,
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
    CONSTRAINT "行业历史行情_pkey" PRIMARY KEY ("行业名称", "日期")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."行业历史行情"
    OWNER to postgres;
-- Index: idx_行业历史行情_板块名称_日期

-- DROP INDEX IF EXISTS public."idx_行业历史行情_板块名称_日期";

CREATE INDEX IF NOT EXISTS "idx_行业历史行情_板块名称_日期"
    ON public."行业历史行情" USING btree
    ("行业名称" COLLATE pg_catalog."default" ASC NULLS LAST, "日期" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_行业历史行情_行业名称_日期

-- DROP INDEX IF EXISTS public."idx_行业历史行情_行业名称_日期";

CREATE INDEX IF NOT EXISTS "idx_行业历史行情_行业名称_日期"
    ON public."行业历史行情" USING btree
    ("行业名称" COLLATE pg_catalog."default" ASC NULLS LAST, "日期" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.指数历史行情

-- DROP TABLE IF EXISTS public."指数历史行情";

CREATE TABLE IF NOT EXISTS public."指数历史行情"
(
    "指数代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "指数名称" character varying(50) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "开盘" double precision NOT NULL,
    "收盘" double precision NOT NULL,
    "最高" double precision NOT NULL,
    "最低" double precision NOT NULL,
    "成交量" numeric(38,0) NOT NULL,
    "成交额" numeric(38,0) NOT NULL,
    "振幅" double precision,
    "涨跌幅" double precision,
    "涨跌额" double precision,
    "换手率" double precision,
    CONSTRAINT "指数历史行情_pkey" PRIMARY KEY ("指数代码", "日期")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."指数历史行情"
    OWNER to postgres;
-- Index: idx_指数历史行情_日期

-- DROP INDEX IF EXISTS public."idx_指数历史行情_日期";

CREATE INDEX IF NOT EXISTS "idx_指数历史行情_日期"
    ON public."指数历史行情" USING btree
    ("日期" ASC NULLS LAST)
    TABLESPACE pg_default;