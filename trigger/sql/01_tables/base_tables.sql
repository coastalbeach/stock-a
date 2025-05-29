-- 文件功能：定义基础数据表，包括除权除息信息表和复权因子表。
-- 创建日期：YYYY-MM-DD (请替换为实际创建日期)
-- 创建人：AI Assistant

-- 清理旧表 (如果存在)
DROP TABLE IF EXISTS public."除权除息信息" CASCADE;
DROP TABLE IF EXISTS public."复权因子表" CASCADE;

-- 表: public.除权除息信息
CREATE TABLE IF NOT EXISTS public."除权除息信息"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "公告日期" date NOT NULL, -- 公告日期
    "股权登记日" date, -- 股权登记日
    "除权除息日" date NOT NULL, -- 除权除息日，关键日期，复权因子变动日
    "方案进度" character varying(50) COLLATE pg_catalog."default", -- 例如：实施、预案等
    "每股送股比例" numeric(18,6) DEFAULT 0, -- 每10股送X股，这里记录每股送股数
    "每股转增比例" numeric(18,6) DEFAULT 0, -- 每10股转增X股，这里记录每股转增数
    "每股派息金额_税前" numeric(18,6) DEFAULT 0, -- 每10股派X元(含税)，这里记录每股派息额
    "配股方案" text COLLATE pg_catalog."default", -- 配股方案描述
    "配股价" numeric(18,6), -- 配股价
    "配股比例" numeric(18,6), -- 每10股配X股，这里记录每股配股数
    "分红说明" text COLLATE pg_catalog."default",
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP, -- 记录更新时间
    CONSTRAINT "除权除息信息_pkey" PRIMARY KEY ("股票代码", "除权除息日", "公告日期") -- 联合主键，允许同一股票同一除权日有不同公告日的记录（虽然少见，但为以防万一）
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."除权除息信息"
    OWNER to postgres;

COMMENT ON TABLE public."除权除息信息"
    IS '存储股票的除权除息信息，用于计算复权因子。';
COMMENT ON COLUMN public."除权除息信息"."公告日期"
    IS '公司发布除权除息预案或实施公告的日期';
COMMENT ON COLUMN public."除权除息信息"."股权登记日"
    IS '有权参与此次分红或配股的股东持股截止日期';
COMMENT ON COLUMN public."除权除息信息"."除权除息日"
    IS '发生除权或除息的日期，股价会进行相应调整，是计算复权因子的关键日期';
COMMENT ON COLUMN public."除权除息信息"."方案进度"
    IS '除权除息方案的当前状态，例如：预案、股东大会通过、实施等';
COMMENT ON COLUMN public."除权除息信息"."每股送股比例"
    IS '每股送红股的数量，例如0.5代表每1股送0.5股 (即10送5)';
COMMENT ON COLUMN public."除权除息信息"."每股转增比例"
    IS '每股资本公积转增股本的数量，例如0.3代表每1股转增0.3股 (即10转3)';
COMMENT ON COLUMN public."除权除息信息"."每股派息金额_税前"
    IS '每股派发现金红利的金额（税前），例如0.25代表每1股派0.25元 (即10派2.5元)';
COMMENT ON COLUMN public."除权除息信息"."配股方案"
    IS '详细的配股方案说明';
COMMENT ON COLUMN public."除权除息信息"."配股价"
    IS '配股时股东购买新股的价格';
COMMENT ON COLUMN public."除权除息信息"."配股比例"
    IS '每股可配售新股的数量，例如0.2代表每1股可配0.2股 (即10配2)';
COMMENT ON COLUMN public."除权除息信息"."分红说明"
    IS '关于分红的其他说明信息';
COMMENT ON COLUMN public."除权除息信息"."更新时间"
    IS '该条记录的最后更新时间';

-- 表: public.复权因子表
CREATE TABLE IF NOT EXISTS public."复权因子表"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "前复权因子" numeric(20,10) DEFAULT 1.0, -- 用于计算前复权价格
    "后复权因子" numeric(20,10) DEFAULT 1.0, -- 用于计算后复权价格
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP, -- 记录更新时间
    CONSTRAINT "复权因子表_pkey" PRIMARY KEY ("股票代码", "日期")
)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."复权因子表"
    OWNER to postgres;

COMMENT ON TABLE public."复权因子表"
    IS '存储股票每日的复权因子，用于将不复权价格转换为前复权或后复权价格。';
COMMENT ON COLUMN public."复权因子表"."前复权因子"
    IS '用于计算前复权价格的因子。前复权：以最新价格为基准，向前调整历史价格。计算公式：前复权价 = 不复权价 * 前复权因子。';
COMMENT ON COLUMN public."复权因子表"."后复权因子"
    IS '用于计算后复权价格的因子。后复权：以最早上市日价格为基准，向后调整历史价格。计算公式：后复权价 = 不复权价 * 后复权因子。';
COMMENT ON COLUMN public."复权因子表"."更新时间"
    IS '该条记录的最后更新时间';

-- 索引 for 复权因子表
CREATE INDEX IF NOT EXISTS idx_adj_factor_stock_code_date
    ON public."复权因子表" USING btree
    ("股票代码" ASC NULLS LAST, "日期" ASC NULLS LAST);

-- 可以在此添加其他基础表的定义

-- 文件结束 --