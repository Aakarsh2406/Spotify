{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    
    {%- if target.name == 'dev' or target.name == 'default' -%}
        {%- if custom_schema_name is none -%}
            {{ default_schema | trim | upper }}
        {%- else -%}
            {{ custom_schema_name | trim | upper }}
        {%- endif %}
    {%- else -%}
        {%- if custom_schema_name is none -%}
            {{ default_schema  | trim | upper }}
        {%- else -%}
            {{ custom_schema_name | trim | upper }}
        {%- endif %}
    {%- endif -%}
{%- endmacro %}
