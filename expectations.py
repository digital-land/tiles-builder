import sqlite3
import pandas as pd


def transform_df_first_column_into_set(dataframe: pd.DataFrame) -> set:
    "Given a pd dataframe returns the first column as a python set"
    return set(dataframe.iloc[:, 0].unique())


class QueryRunner:
    "Class to run queries usings spatialite"

    def __init__(self, tested_dataset_path: str):
        "Receives a path/name of sqlite dataset against which it will run the queries"
        self.tested_dataset_path = tested_dataset_path

    def inform_dataset_path(self):
        return self.tested_dataset_path

    def run_query(self, sql_query: str, return_only_first_col_as_set: bool = False):
        """
        Receives a sql query and returns the results either in a pandas
        dataframe or just the first column as a set (this is useful to
        test presence or absence of items like tables, columns, etc).
        Note: connection is openned and closed at each query, but for use
        cases like the present one that would not offer big benefits and
        would mean having to dev thread-lcoal connection pools. For more
        info see: https://stackoverflow.com/a/14520670
        """
        with sqlite3.connect(self.tested_dataset_path) as con:
            cursor = con.execute(sql_query)
            cols = [column[0] for column in cursor.description]
            results = pd.DataFrame.from_records(data=cursor.fetchall(), columns=cols)

        if return_only_first_col_as_set:
            return transform_df_first_column_into_set(results)
        else:
            return results


def expect_custom_query_result_to_be_as_predicted(
        query_runner: QueryRunner,
        custom_query: str,
        expected_query_result: list,
        **kwargs,
):
    """Receives a custom sqlite/spatialite query as string and a expected
    result in the form of list of row dictionaires, for example, 3 rows
    would look like this:
    [{'col_name1': value1, 'col_name_2': value2, 'col_name_3': value3},
     {'col_name1': value1, 'col_name_2': value2, 'col_name_3': value3},
     {'col_name1': value1, 'col_name_2': value2, 'col_name_3': value3}]
    Returns True if the result for the query are as expected and False
    otherwise, with details.
    """
    query_result = query_runner.run_query(custom_query)

    result = query_result.to_dict(orient="records") == expected_query_result

    if result:
        msg = "Success: data quality as expected"
        details = None
    else:
        msg = "Fail: result for custom query was not as expected, see details"
        details = {
            "custom_query": custom_query,
            "query_result": query_result.to_dict(orient="records"),
            "expected_query_result": expected_query_result,
        }

    return result, msg, details


def expect_filtered_entities_to_be_as_predicted(
        query_runner: QueryRunner,
        expected_result: list,
        columns=None,
        filters: dict = None,
        **kwargs,
):
    possible_filters = ["organisation_entity", "reference"]
    if any(filter not in possible_filters for filter in filters.keys()):
        for filter in filters.keys():
            print(filter not in possible_filters)
        raise ValueError("unsupported filters being used")

    custom_query = f"""
        {build_entity_select_statement(columns)}
        FROM entity
        {build_entity_where_clause(filters)}
        ;
    """

    actual_result = query_runner.run_query(custom_query).to_dict(orient="records")
    result = actual_result == expected_result

    details = {
        "actual_result": actual_result,
        "expected_result": expected_result,
    }
    if result:
        msg = "Success: data quality as expected"
    else:
        msg = "Fail: result count is not correct, see details"

    return result, msg, details


def build_entity_select_statement(columns):
    """
    function to be used to build a select statement for the entity table
    in the dataset created via the dataset package. Specifically to help
    pull out information stored in the json fields
    """
    possible_entity_columns = [
        "dataset",
        "end_date",
        "entity",
        "entry_date",
        "geojson",
        "geometry",
        "json",
        "name",
        "organisation_entity",
        "point",
        "prefix",
        "reference",
        "start_date",
        "typology",
    ]

    entity_columns = [col for col in columns if col in possible_entity_columns]
    json_columns = [
        f"json_extract(json,'$.{col}') as '{col}'"
        for col in columns
        if col not in possible_entity_columns
    ]
    final_columns = [*entity_columns, *json_columns]
    select_statement = f"SELECT {','.join(final_columns)}"

    return select_statement


def build_entity_where_clause(filters):
    """
    Function to produce sql WHERE clause for the entity table given a dictionary of filters
    """
    possible_filters = [
        "dataset",
        "entity",
        "geometry",
        "json",
        "name",
        "organisation_entity",
        "point",
        "prefix",
        "reference",
        "typology",
    ]

    if any(filter not in possible_filters for filter in filters.keys()):
        unsupported_filters = [
            filter for filter in filters.keys() if filter not in possible_filters
        ]
        raise ValueError(
            f'unsupported filters {",".join(unsupported_filters)} being used'
        )

    for filter in filters.keys():
        filter_values = filters[filter]
        filter_conditions = []
        if filter in ["geometry", "point"]:
            if isinstance(filter_values, str):
                filter_conditions.append(
                    f"ST_Intersects(GeomFromText({filter}),GeomFromText('{filter_values}'))"
                )
            else:
                raise TypeError(f"{filter} value must be a single wkt as a string")
        elif isinstance(filter_values, str) or isinstance(filter_values, int):
            filter_values = f"{filter_values}".replace("'", "''")
            filter_conditions.append(f"{filter} = '{filter_values}'")
        elif isinstance(filter_values, list):
            filter_values = [
                filter_value.replace("'", "''") for filter_value in filter_values
            ]
            filter_values = [f"'{filter_value}'" for filter_value in filter_values]
            filter_conditions.append(f"{filter} in ({','.join(filter_values)})")
        else:
            raise TypeError(f"{filter} must be either an int, str or a list")

    where_clause_sql = f"WHERE {' AND '.join(filter_conditions)}"

    return where_clause_sql

