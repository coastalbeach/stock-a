-- 基础表：股票基本信息

-- Table: public.股票基本信息

-- DROP TABLE IF EXISTS public."股票基本信息";

CREATE TABLE IF NOT EXISTS public."股票基本信息"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "股票名称" character varying(50) COLLATE pg_catalog."default" NOT NULL,
    "市场" character varying(10) COLLATE pg_catalog."default",
    "所属行业" character varying(50) COLLATE pg_catalog."default",
    "市值等级" character varying(10) COLLATE pg_catalog."default",
    "市盈率-动态" double precision,
    "市净率" double precision,
    "总市值" double precision,
    "流通市值" double precision,
    "60日均涨幅" double precision,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "股票基本信息_pkey" PRIMARY KEY ("股票代码")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票基本信息"
    OWNER to postgres;
-- Index: idx_市值等级

-- DROP INDEX IF EXISTS public."idx_市值等级";

CREATE INDEX IF NOT EXISTS "idx_市值等级"
    ON public."股票基本信息" USING btree
    ("市值等级" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_所属行业

-- DROP INDEX IF EXISTS public."idx_所属行业";

CREATE INDEX IF NOT EXISTS "idx_所属行业"
    ON public."股票基本信息" USING btree
    ("所属行业" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_股票名称

-- DROP INDEX IF EXISTS public."idx_股票名称";

CREATE INDEX IF NOT EXISTS "idx_股票名称"
    ON public."股票基本信息" USING btree
    ("股票名称" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- 基础表：概念板块

-- Table: public.概念板块

-- DROP TABLE IF EXISTS public."概念板块";

CREATE TABLE IF NOT EXISTS public."概念板块"
(
    "板块代码" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "板块名称" character varying(50) COLLATE pg_catalog."default" NOT NULL,
    "最新价" numeric(20,2),
    "涨跌额" numeric(20,2),
    "涨跌幅" numeric(10,2),
    "总市值" bigint,
    "换手率" numeric(10,2),
    "上涨家数" integer,
    "下跌家数" integer,
    "领涨股票" character varying(20) COLLATE pg_catalog."default",
    "领涨股票涨跌幅" numeric(10,2),
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "概念板块_pkey" PRIMARY KEY ("板块代码")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."概念板块"
    OWNER to postgres;


-- 基础表：行业板块

-- Table: public.行业板块

-- DROP TABLE IF EXISTS public."行业板块";

CREATE TABLE IF NOT EXISTS public."行业板块"
(
    "板块代码" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "行业名称" character varying(50) COLLATE pg_catalog."default" NOT NULL,
    "最新价" numeric(20,2),
    "涨跌额" numeric(20,2),
    "涨跌幅" numeric(10,2),
    "总市值" bigint,
    "换手率" numeric(10,2),
    "上涨家数" integer,
    "下跌家数" integer,
    "领涨股票" character varying(20) COLLATE pg_catalog."default",
    "领涨股票涨跌幅" numeric(10,2),
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "行业板块_pkey" PRIMARY KEY ("板块代码")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."行业板块"
    OWNER to postgres;