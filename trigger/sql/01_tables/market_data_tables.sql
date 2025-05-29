-- 文件功能：定义行情数据相关的表，包括周频和月频的普通行情及后复权行情表。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧表 (如果存在)
DROP TABLE IF EXISTS public."股票历史行情_周频" CASCADE;
DROP TABLE IF EXISTS public."股票历史行情_月频" CASCADE;
DROP TABLE IF EXISTS public."股票历史行情_周频_后复权" CASCADE;
DROP TABLE IF EXISTS public."股票历史行情_月频_后复权" CASCADE;

-- 表: public.股票历史行情_周频
CREATE TABLE IF NOT EXISTS public."股票历史行情_周频"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "周期开始日期" date NOT NULL, -- 每周的第一个交易日
    "周期结束日期" date NOT NULL, -- 每周的最后一个交易日
    "开盘" numeric(18,4), -- 周期内第一个交易日的开盘价
    "收盘" numeric(18,4), -- 周期内最后一个交易日的收盘价
    "最高" numeric(18,4), -- 周期内的最高价
    "最低" numeric(18,4), -- 周期内的最低价
    "成交量" numeric(20,0), -- 周期内的总成交量
    "成交额" numeric(20,4), -- 周期内的总成交额
    "涨跌幅" numeric(10,4), -- 周期内的涨跌幅（百分比）
    "涨跌额" numeric(10,4), -- 周期内的涨跌额
    "交易日数" integer, -- 周期内的交易日数量
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "股票历史行情_周频_pkey" PRIMARY KEY ("股票代码", "周期结束日期")
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_周频"
    OWNER to postgres;

COMMENT ON TABLE public."股票历史行情_周频"
    IS '存储股票的周频历史行情数据，由日频数据聚合生成';
-- ... (省略其他列的注释，保持与原文件一致) ...

-- 创建索引 for 股票历史行情_周频
CREATE INDEX IF NOT EXISTS idx_weekly_stock_code_date
    ON public."股票历史行情_周频" USING btree
    ("股票代码" ASC NULLS LAST, "周期结束日期" DESC NULLS LAST);

-- 表: public.股票历史行情_月频
CREATE TABLE IF NOT EXISTS public."股票历史行情_月频"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "周期开始日期" date NOT NULL, -- 每月的第一个交易日
    "周期结束日期" date NOT NULL, -- 每月的最后一个交易日
    "开盘" numeric(18,4), -- 周期内第一个交易日的开盘价
    "收盘" numeric(18,4), -- 周期内最后一个交易日的收盘价
    "最高" numeric(18,4), -- 周期内的最高价
    "最低" numeric(18,4), -- 周期内的最低价
    "成交量" numeric(20,0), -- 周期内的总成交量
    "成交额" numeric(20,4), -- 周期内的总成交额
    "涨跌幅" numeric(10,4), -- 周期内的涨跌幅（百分比）
    "涨跌额" numeric(10,4), -- 周期内的涨跌额
    "交易日数" integer, -- 周期内的交易日数量
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "股票历史行情_月频_pkey" PRIMARY KEY ("股票代码", "周期结束日期")
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_月频"
    OWNER to postgres;

COMMENT ON TABLE public."股票历史行情_月频"
    IS '存储股票的月频历史行情数据，由日频数据聚合生成';
-- ... (省略其他列的注释，保持与原文件一致) ...

-- 创建索引 for 股票历史行情_月频
CREATE INDEX IF NOT EXISTS idx_monthly_stock_code_date
    ON public."股票历史行情_月频" USING btree
    ("股票代码" ASC NULLS LAST, "周期结束日期" DESC NULLS LAST);

-- 表: public.股票历史行情_周频_后复权
CREATE TABLE IF NOT EXISTS public."股票历史行情_周频_后复权"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "周期开始日期" date NOT NULL, -- 每周的第一个交易日
    "周期结束日期" date NOT NULL, -- 每周的最后一个交易日
    "开盘" numeric(18,4), -- 周期内第一个交易日的开盘价
    "收盘" numeric(18,4), -- 周期内最后一个交易日的收盘价
    "最高" numeric(18,4), -- 周期内的最高价
    "最低" numeric(18,4), -- 周期内的最低价
    "成交量" numeric(20,0), -- 周期内的总成交量
    "成交额" numeric(20,4), -- 周期内的总成交额
    "涨跌幅" numeric(10,4), -- 周期内的涨跌幅（百分比）
    "涨跌额" numeric(10,4), -- 周期内的涨跌额
    "交易日数" integer, -- 周期内的交易日数量
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "股票历史行情_周频_后复权_pkey" PRIMARY KEY ("股票代码", "周期结束日期")
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_周频_后复权"
    OWNER to postgres;

COMMENT ON TABLE public."股票历史行情_周频_后复权"
    IS '存储股票的周频后复权历史行情数据，由日频后复权数据聚合生成';
-- ... (省略其他列的注释，保持与原文件一致) ...

-- 创建索引 for 股票历史行情_周频_后复权
CREATE INDEX IF NOT EXISTS idx_weekly_hfq_stock_code_date
    ON public."股票历史行情_周频_后复权" USING btree
    ("股票代码" ASC NULLS LAST, "周期结束日期" DESC NULLS LAST);

-- 表: public.股票历史行情_月频_后复权
CREATE TABLE IF NOT EXISTS public."股票历史行情_月频_后复权"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "周期开始日期" date NOT NULL, -- 每月的第一个交易日
    "周期结束日期" date NOT NULL, -- 每月的最后一个交易日
    "开盘" numeric(18,4), -- 周期内第一个交易日的开盘价
    "收盘" numeric(18,4), -- 周期内最后一个交易日的收盘价
    "最高" numeric(18,4), -- 周期内的最高价
    "最低" numeric(18,4), -- 周期内的最低价
    "成交量" numeric(20,0), -- 周期内的总成交量
    "成交额" numeric(20,4), -- 周期内的总成交额
    "涨跌幅" numeric(10,4), -- 周期内的涨跌幅（百分比）
    "涨跌额" numeric(10,4), -- 周期内的涨跌额
    "交易日数" integer, -- 周期内的交易日数量
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "股票历史行情_月频_后复权_pkey" PRIMARY KEY ("股票代码", "周期结束日期")
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票历史行情_月频_后复权"
    OWNER to postgres;

COMMENT ON TABLE public."股票历史行情_月频_后复权"
    IS '存储股票的月频后复权历史行情数据，由日频后复权数据聚合生成';
-- ... (省略其他列的注释，保持与原文件一致) ...

-- 创建索引 for 股票历史行情_月频_后复权
CREATE INDEX IF NOT EXISTS idx_monthly_hfq_stock_code_date
    ON public."股票历史行情_月频_后复权" USING btree
    ("股票代码" ASC NULLS LAST, "周期结束日期" DESC NULLS LAST);

-- 文件结束 --