-- 财务报表相关表：利润表、现金流量表、资产负债表、财务指标

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