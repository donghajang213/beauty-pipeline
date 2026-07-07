{#-
파일: dbt/macros/generate_schema_name.sql
역할: 모델의 +schema 값을 데이터셋 이름으로 "그대로" 쓰게 하는 표준 오버라이드.
왜: dbt 기본 동작은 "기본데이터셋_커스텀" 으로 이어붙여서(staging_marts 같은)
    Terraform으로 만든 깔끔한 데이터셋 이름(staging, marts)과 어긋난다.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
