-- 龙虎榜相关表：龙虎榜详情、个股上榜统计

-- Table: public.龙虎榜详情

-- DROP TABLE IF EXISTS public."龙虎榜详情";

CREATE TABLE IF NOT EXISTS public."龙虎榜详情"
(
    "代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "名称" character varying(50) COLLATE pg_catalog."default",
    "上榜日" date NOT NULL,
    "解读" text COLLATE pg_catalog."default",
    "收盘价" double precision,
    "涨跌幅" double precision,
    "龙虎榜净买额" double precision,
    "龙虎榜买入额" double precision,
    "龙虎榜卖出额" double precision,
    "龙虎榜成交额" double precision,
    "市场总成交额" bigint,
    "净买额占总成交比" double precision,
    "成交额占总成交比" double precision,
    "换手率" double precision,
    "流通市值" double precision,
    "上榜原因" text COLLATE pg_catalog."default" NOT NULL,
    "上榜后1日" double precision,
    "上榜后2日" double precision,
    "上榜后5日" double precision,
    "上榜后10日" double precision,
    CONSTRAINT "龙虎榜详情_pkey" PRIMARY KEY ("代码", "上榜日", "上榜原因")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."龙虎榜详情"
    OWNER to postgres;
-- Index: idx_lhb_detail_上榜原因

-- DROP INDEX IF EXISTS public."idx_lhb_detail_上榜原因";

CREATE INDEX IF NOT EXISTS "idx_lhb_detail_上榜原因"
    ON public."龙虎榜详情" USING btree
    ("上榜原因" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_lhb_detail_上榜日

-- DROP INDEX IF EXISTS public."idx_lhb_detail_上榜日";

CREATE INDEX IF NOT EXISTS "idx_lhb_detail_上榜日"
    ON public."龙虎榜详情" USING btree
    ("上榜日" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_lhb_detail_代码

-- DROP INDEX IF EXISTS public."idx_lhb_detail_代码";

CREATE INDEX IF NOT EXISTS "idx_lhb_detail_代码"
    ON public."龙虎榜详情" USING btree
    ("代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.个股上榜统计

-- DROP TABLE IF EXISTS public."个股上榜统计";

CREATE TABLE IF NOT EXISTS public."个股上榜统计"
(
    "序号" integer NOT NULL DEFAULT nextval('"个股上榜统计_序号_seq"'::regclass),
    "代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "名称" character varying(50) COLLATE pg_catalog."default" NOT NULL,
    "最近上榜日" date NOT NULL,
    "收盘价" double precision,
    "涨跌幅" double precision,
    "上榜次数" integer,
    "龙虎榜净买额" double precision,
    "龙虎榜买入额" double precision,
    "龙虎榜卖出额" double precision,
    "龙虎榜总成交额" double precision,
    "买方机构次数" integer,
    "卖方机构次数" integer,
    "机构买入净额" double precision,
    "机构买入总额" double precision,
    "机构卖出总额" double precision,
    "近1个月涨跌幅" double precision,
    "近3个月涨跌幅" double precision,
    "近6个月涨跌幅" double precision,
    "近1年涨跌幅" double precision,
    "统计周期" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "个股上榜统计_pkey" PRIMARY KEY ("代码", "统计周期")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."个股上榜统计"
    OWNER to postgres;
-- Index: idx_lhb_stock_statistic_上榜次数

-- DROP INDEX IF EXISTS public."idx_lhb_stock_statistic_上榜次数";

CREATE INDEX IF NOT EXISTS "idx_lhb_stock_statistic_上榜次数"
    ON public."个股上榜统计" USING btree
    ("上榜次数" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_lhb_stock_statistic_代码

-- DROP INDEX IF EXISTS public."idx_lhb_stock_statistic_代码";

CREATE INDEX IF NOT EXISTS "idx_lhb_stock_statistic_代码"
    ON public."个股上榜统计" USING btree
    ("代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_lhb_stock_statistic_最近上榜日

-- DROP INDEX IF EXISTS public."idx_lhb_stock_statistic_最近上榜日";

CREATE INDEX IF NOT EXISTS "idx_lhb_stock_statistic_最近上榜日"
    ON public."个股上榜统计" USING btree
    ("最近上榜日" ASC NULLS LAST)
    TABLESPACE pg_default;