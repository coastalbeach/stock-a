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


-- Table: public.利润表

-- DROP TABLE IF EXISTS public."利润表";

CREATE TABLE IF NOT EXISTS public."利润表"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "报告期" date NOT NULL,
    "报表类型" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "营业总收入" double precision,
    "营业收入" double precision,
    "营业总成本" double precision,
    "营业成本" double precision,
    "销售费用" double precision,
    "管理费用" double precision,
    "研发费用" double precision,
    "财务费用" double precision,
    "投资收益" double precision,
    "公允价值变动收益" double precision,
    "营业利润" double precision,
    "营业外收入" double precision,
    "营业外支出" double precision,
    "利润总额" double precision,
    "所得税费用" double precision,
    "净利润" double precision,
    "归属于母公司股东的净利润" double precision,
    "少数股东损益" double precision,
    "基本每股收益" double precision,
    "稀释每股收益" double precision,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "利润表_pkey" PRIMARY KEY ("股票代码", "报告期", "报表类型")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."利润表"
    OWNER to postgres;
-- Index: idx_profit_报告期

-- DROP INDEX IF EXISTS public."idx_profit_报告期";

CREATE INDEX IF NOT EXISTS "idx_profit_报告期"
    ON public."利润表" USING btree
    ("报告期" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_profit_股票代码

-- DROP INDEX IF EXISTS public."idx_profit_股票代码";

CREATE INDEX IF NOT EXISTS "idx_profit_股票代码"
    ON public."利润表" USING btree
    ("股票代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.现金流量表

-- DROP TABLE IF EXISTS public."现金流量表";

CREATE TABLE IF NOT EXISTS public."现金流量表"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "报告期" date NOT NULL,
    "报表类型" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "经营活动产生的现金流量净额" double precision,
    "销售商品、提供劳务收到的现金" double precision,
    "收到的税费返还" double precision,
    "收到其他与经营活动有关的现金" double precision,
    "经营活动现金流入小计" double precision,
    "购买商品、接受劳务支付的现金" double precision,
    "支付给职工以及为职工支付的现金" double precision,
    "支付的各项税费" double precision,
    "支付其他与经营活动有关的现金" double precision,
    "经营活动现金流出小计" double precision,
    "投资活动产生的现金流量净额" double precision,
    "收回投资收到的现金" double precision,
    "取得投资收益收到的现金" double precision,
    "处置固定资产、无形资产和其他长期资产收回的" double precision,
    "投资活动现金流入小计" double precision,
    "购建固定资产、无形资产和其他长期资产支付的" double precision,
    "投资支付的现金" double precision,
    "投资活动现金流出小计" double precision,
    "筹资活动产生的现金流量净额" double precision,
    "吸收投资收到的现金" double precision,
    "取得借款收到的现金" double precision,
    "筹资活动现金流入小计" double precision,
    "偿还债务支付的现金" double precision,
    "分配股利、利润或偿付利息支付的现金" double precision,
    "筹资活动现金流出小计" double precision,
    "现金及现金等价物净增加额" double precision,
    "期初现金及现金等价物余额" double precision,
    "期末现金及现金等价物余额" double precision,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "现金流量表_pkey" PRIMARY KEY ("股票代码", "报告期", "报表类型")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."现金流量表"
    OWNER to postgres;
-- Index: idx_cash_flow_报告期

-- DROP INDEX IF EXISTS public."idx_cash_flow_报告期";

CREATE INDEX IF NOT EXISTS "idx_cash_flow_报告期"
    ON public."现金流量表" USING btree
    ("报告期" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_cash_flow_股票代码

-- DROP INDEX IF EXISTS public."idx_cash_flow_股票代码";

CREATE INDEX IF NOT EXISTS "idx_cash_flow_股票代码"
    ON public."现金流量表" USING btree
    ("股票代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.资产负债表

-- DROP TABLE IF EXISTS public."资产负债表";

CREATE TABLE IF NOT EXISTS public."资产负债表"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "报告期" date NOT NULL,
    "报表类型" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "货币资金" double precision,
    "交易性金融资产" double precision,
    "应收票据" double precision,
    "应收账款" double precision,
    "应收款项融资" double precision,
    "预付款项" double precision,
    "其他应收款" double precision,
    "存货" double precision,
    "流动资产合计" double precision,
    "长期股权投资" double precision,
    "固定资产" double precision,
    "在建工程" double precision,
    "无形资产" double precision,
    "商誉" double precision,
    "非流动资产合计" double precision,
    "资产总计" double precision,
    "短期借款" double precision,
    "应付票据" double precision,
    "应付账款" double precision,
    "预收款项" double precision,
    "应付职工薪酬" double precision,
    "应交税费" double precision,
    "其他应付款" double precision,
    "流动负债合计" double precision,
    "长期借款" double precision,
    "应付债券" double precision,
    "非流动负债合计" double precision,
    "负债合计" double precision,
    "实收资本" double precision,
    "资本公积" double precision,
    "盈余公积" double precision,
    "未分配利润" double precision,
    "归属于母公司股东权益合计" double precision,
    "股东权益合计" double precision,
    "负债和股东权益总计" double precision,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "资产负债表_pkey" PRIMARY KEY ("股票代码", "报告期", "报表类型")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."资产负债表"
    OWNER to postgres;
-- Index: idx_balance_报告期

-- DROP INDEX IF EXISTS public."idx_balance_报告期";

CREATE INDEX IF NOT EXISTS "idx_balance_报告期"
    ON public."资产负债表" USING btree
    ("报告期" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_balance_股票代码

-- DROP INDEX IF EXISTS public."idx_balance_股票代码";

CREATE INDEX IF NOT EXISTS "idx_balance_股票代码"
    ON public."资产负债表" USING btree
    ("股票代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.财务指标

-- DROP TABLE IF EXISTS public."财务指标";

CREATE TABLE IF NOT EXISTS public."财务指标"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "报告期" date NOT NULL,
    "指标类型" character varying(20) COLLATE pg_catalog."default" NOT NULL,
    "更新时间" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    "净利润" character varying(50) COLLATE pg_catalog."default",
    "净利润同比增长率" character varying(50) COLLATE pg_catalog."default",
    "扣非净利润" character varying(50) COLLATE pg_catalog."default",
    "扣非净利润同比增长率" character varying(50) COLLATE pg_catalog."default",
    "营业总收入" character varying(50) COLLATE pg_catalog."default",
    "营业总收入同比增长率" character varying(50) COLLATE pg_catalog."default",
    "基本每股收益" character varying(50) COLLATE pg_catalog."default",
    "每股净资产" character varying(50) COLLATE pg_catalog."default",
    "每股资本公积金" character varying(50) COLLATE pg_catalog."default",
    "每股未分配利润" character varying(50) COLLATE pg_catalog."default",
    "每股经营现金流" character varying(50) COLLATE pg_catalog."default",
    "销售净利率" character varying(50) COLLATE pg_catalog."default",
    "销售毛利率" character varying(50) COLLATE pg_catalog."default",
    "净资产收益率" character varying(50) COLLATE pg_catalog."default",
    "净资产收益率-摊薄" character varying(50) COLLATE pg_catalog."default",
    "营业周期" character varying(50) COLLATE pg_catalog."default",
    "存货周转率" character varying(50) COLLATE pg_catalog."default",
    "存货周转天数" character varying(50) COLLATE pg_catalog."default",
    "应收账款周转天数" character varying(50) COLLATE pg_catalog."default",
    "流动比率" character varying(50) COLLATE pg_catalog."default",
    "速动比率" character varying(50) COLLATE pg_catalog."default",
    "保守速动比率" character varying(50) COLLATE pg_catalog."default",
    "产权比率" character varying(50) COLLATE pg_catalog."default",
    "资产负债率" character varying(50) COLLATE pg_catalog."default",
    CONSTRAINT "财务指标_pkey" PRIMARY KEY ("股票代码", "报告期", "指标类型")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."财务指标"
    OWNER to postgres;
-- Index: idx_financial_indicator_报告期

-- DROP INDEX IF EXISTS public."idx_financial_indicator_报告期";

CREATE INDEX IF NOT EXISTS "idx_financial_indicator_报告期"
    ON public."财务指标" USING btree
    ("报告期" ASC NULLS LAST)
    TABLESPACE pg_default;
-- Index: idx_financial_indicator_股票代码

-- DROP INDEX IF EXISTS public."idx_financial_indicator_股票代码";

CREATE INDEX IF NOT EXISTS "idx_financial_indicator_股票代码"
    ON public."财务指标" USING btree
    ("股票代码" COLLATE pg_catalog."default" ASC NULLS LAST)
    TABLESPACE pg_default;


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


-- Table: public.股票技术指标

-- DROP TABLE IF EXISTS public."股票技术指标";

CREATE TABLE IF NOT EXISTS public."股票技术指标"
(
    "股票代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "股票技术指标_pkey" PRIMARY KEY ("股票代码", "日期"),
    CONSTRAINT "股票技术指标_fkey" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_0" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey1" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_1" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey10" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_10" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey11" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_11" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey12" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_12" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey13" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_13" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey14" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_14" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey15" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_15" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey2" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_2" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey3" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_3" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey4" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_4" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey5" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_5" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey6" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_6" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey7" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_7" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey8" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_8" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE,
    CONSTRAINT "股票技术指标_股票代码_日期_fkey9" FOREIGN KEY ("股票代码", "日期")
        REFERENCES public."股票历史行情_后复权_9" ("股票代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
) PARTITION BY HASH ("股票代码");

ALTER TABLE IF EXISTS public."股票技术指标"
    OWNER to postgres;
-- Index: idx_股票技术指标_日期

-- DROP INDEX IF EXISTS public."idx_股票技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_股票技术指标_日期"
    ON public."股票技术指标" USING btree
    ("日期" ASC NULLS LAST)
;

-- Partitions SQL

CREATE TABLE public."股票技术指标_p0" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 0)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p0"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p1" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 1)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p1"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p10" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 10)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p10"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p11" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 11)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p11"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p12" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 12)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p12"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p13" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 13)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p13"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p14" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 14)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p14"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p15" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 15)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p15"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p2" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 2)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p2"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p3" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 3)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p3"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p4" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 4)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p4"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p5" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 5)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p5"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p6" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 6)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p6"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p7" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 7)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p7"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p8" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 8)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p8"
    OWNER to postgres;
CREATE TABLE public."股票技术指标_p9" PARTITION OF public."股票技术指标"
    FOR VALUES WITH (modulus 16, remainder 9)
TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."股票技术指标_p9"
    OWNER to postgres;


-- Table: public.行业技术指标

-- DROP TABLE IF EXISTS public."行业技术指标";

CREATE TABLE IF NOT EXISTS public."行业技术指标"
(
    "行业名称" character varying(100) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "行业技术指标_pkey" PRIMARY KEY ("行业名称", "日期"),
    CONSTRAINT "行业技术指标_fkey" FOREIGN KEY ("行业名称", "日期")
        REFERENCES public."行业历史行情" ("行业名称", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."行业技术指标"
    OWNER to postgres;
-- Index: idx_行业技术指标_日期

-- DROP INDEX IF EXISTS public."idx_行业技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_行业技术指标_日期"
    ON public."行业技术指标" USING btree
    ("日期" ASC NULLS LAST)
    TABLESPACE pg_default;


-- Table: public.指数技术指标

-- DROP TABLE IF EXISTS public."指数技术指标";

CREATE TABLE IF NOT EXISTS public."指数技术指标"
(
    "指数代码" character varying(10) COLLATE pg_catalog."default" NOT NULL,
    "日期" date NOT NULL,
    "SMA5" double precision,
    "SMA10" double precision,
    "SMA20" double precision,
    "SMA60" double precision,
    "EMA12" double precision,
    "EMA26" double precision,
    "DIF" double precision,
    "DEA" double precision,
    "MACD_hist" double precision,
    "RSI6" double precision,
    "RSI12" double precision,
    "RSI24" double precision,
    "BBANDS_UPPER" double precision,
    "BBANDS_MIDDLE" double precision,
    "BBANDS_LOWER" double precision,
    "KDJ_K" double precision,
    "KDJ_D" double precision,
    "KDJ_J" double precision,
    "VOL_MA5" double precision,
    "VOL_MA10" double precision,
    "WR14" double precision,
    "CCI14" double precision,
    "PDI14" double precision,
    "MDI14" double precision,
    "ADX14" double precision,
    "ROC6" double precision,
    "ROC12" double precision,
    "BIAS6" double precision,
    "BIAS12" double precision,
    "BIAS24" double precision,
    "OBV" double precision,
    "OBV_MA5" double precision,
    "OBV_MA10" double precision,
    CONSTRAINT "指数技术指标_pkey" PRIMARY KEY ("指数代码", "日期"),
    CONSTRAINT "指数技术指标_fkey" FOREIGN KEY ("指数代码", "日期")
        REFERENCES public."指数历史行情" ("指数代码", "日期") MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS public."指数技术指标"
    OWNER to postgres;
-- Index: idx_指数技术指标_日期

-- DROP INDEX IF EXISTS public."idx_指数技术指标_日期";

CREATE INDEX IF NOT EXISTS "idx_指数技术指标_日期"
    ON public."指数技术指标" USING btree
    ("日期" ASC NULLS LAST)
    TABLESPACE pg_default;