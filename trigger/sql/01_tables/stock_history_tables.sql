-- 文件功能：定义股票历史行情相关的表，包括不复权和后复权表。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧表 (如果存在)
DROP TABLE IF EXISTS public."股票历史行情_不复权" CASCADE;
DROP TABLE IF EXISTS public."股票历史行情_后复权" CASCADE;

-- Table: public.股票历史行情_不复权
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
);

ALTER TABLE IF EXISTS public."股票历史行情_不复权"
    OWNER to postgres;

-- Index: idx_no_adjust_date
CREATE INDEX IF NOT EXISTS idx_no_adjust_date
    ON public."股票历史行情_不复权" USING btree
    ("日期" ASC NULLS LAST);

COMMENT ON TABLE public."股票历史行情_不复权"
    IS '存储股票的不复权历史行情数据';

-- Table: public.股票历史行情_后复权
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
);

ALTER TABLE IF EXISTS public."股票历史行情_后复权"
    OWNER to postgres;

-- Index: idx_hfq_date
CREATE INDEX IF NOT EXISTS idx_hfq_date
    ON public."股票历史行情_后复权" USING btree
    ("日期" ASC NULLS LAST);

COMMENT ON TABLE public."股票历史行情_后复权"
    IS '存储股票的后复权历史行情数据';

-- 文件结束 --