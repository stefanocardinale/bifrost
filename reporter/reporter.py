# -*- coding: utf-8 -*-
import os
import sys
import urllib.parse as urlparse
import datetime
from io import StringIO

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_auth
import pandas as pd
import numpy as np
from bson import json_util
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
from plotly import tools
from dash.dependencies import Input, Output, State

from flask import request   # To get client IP for pass/fail stamp

import dash_scroll_up

import keys

import components.mongo_interface
import components.import_data as import_data
from components.table import html_table, html_td_percentage
from components.filter import html_div_filter, generate_table
from components.sample_report import SAMPLE_PAGESIZE, sample_report, children_sample_list_report, generate_sample_folder
from components.images import list_of_images, static_image_route, image_directory
import components.global_vars as global_vars
import components.admin as admin
from run_checker import pipeline_report

# Globals
# also defined in mongo_interface.py


def hex_to_rgb(value):
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))


def short_species(species):
    if species is None or pd.isna(species):
        return None
    words = species.split(" ")
    if len(words) == 1:
        return species
    return "{}. {}".format(words[0][0], " ".join(words[1:]))


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "bifrost"
app.config["suppress_callback_exceptions"] = True

if hasattr(keys, "pass_protected") and keys.pass_protected:
    dash_auth.BasicAuth(
        app,
        keys.USERNAME_PASSWORD
    )

# Temp css to make it look nice
# Lato font
app.css.append_css(
    {"external_url": "https://fonts.googleapis.com/css?family=Lato"})

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    # To store url param values
    dcc.Store(id="sample-store", data=[], storage_type='session'),
    dcc.Store(id="param-store", data={}),
    dbc.Navbar(
        [
            dbc.Col(
                html.A(
                    # Use row and col to control vertical alignment of logo / brand
                    html.Img(src="assets/img/bifrost-logo-white@2x.png",
                            className="navbar-logo "),
                    href="https://plot.ly",
                        className=" mr-0"
                ),
                sm=3,
                md=2,
                className="navbar-brand text-center"
            ),
            dbc.NavbarToggler(id="navbar-toggler"),
        ],
        color="dark",
        dark=True,
        className="navbar navbar-dark fixed-top bg-dark flex-md-nowrap p-0 shadow"
    ),
    dbc.Container([
        html.Div(className="row", children=[
            html.Div([
                html.Div([
                    dbc.Nav([
                        dbc.NavItem(dcc.Link("Filter",
                                             href="/",
                                             className="nav-link active")),
                        dbc.NavItem(dcc.Link("Aggregate Data",
                                             className="nav-link active",
                                             href="/aggregate")),
                        dbc.NavItem(dcc.Link("Per Sample Data",
                                             className="nav-link active",
                                             href="/sample-report")),
                        dbc.NavItem(dcc.Link("Pipeline Status",
                                             className="nav-link active",
                                             href="pipeline-report")),
                    ], vertical=True),
                    html.Div([
                        html.H6(
                            "Selected samples",
                            className=("sidebar-heading d-flex "
                                       "justify-content-between align-items-center"
                                       " px-3 mt-4 mb-1 text-muted")),
                        html.Div(
                            dbc.Table(size="sm", id="selected-samples")
                            , className="selected-samples-table"),
                    ], className="selected-samples-nav"),
                ], className="sidebar-sticky position-relative"),
            ], className="col-md-2 bg-light sidebar"),
            html.Main([
                html.Div(id="selected-view"),
                    # 
                    # html.Div(id="placeholder1", style={"display": "none"}),
                    # html.Div(id="placeholder2", style={"display": "none"}),
                    # dash_scroll_up.DashScrollUp(
                    #     id="input",
                    #     label="UP",
                    #     className="button button-primary no-print"
                    # ),
                    # html.Div(dash_table.DataTable(editable=False), style={"display": "none"}),
                    # html.H1("bifrost report", style={"display": "none"}),
                    # html.Img(
                    #     src="/assets/img/report.png",
                    #     className="main-logo"
                    # ),
                    # html.H2("Loading...", id="run-name", style={"display": "none"}),
                    # html.Div([
                    #     html.Div(id="report-link", className="u-pull-left"),
                    #     html.H6(html.A("Wiki", href="https://teams.microsoft.com/l/channel/19%3a7b0b9a088602419e9f84630bacc84c2e%40thread.skype/tab%3a%3a9098abb1-75f5-410a-9011-87db7d42f3c2?label=Wiki&groupId=16852743-838a-400e-921d-6c50cc495b2f&tenantId=d0155445-8a4c-4780-9c13-33c78f22890e"), className="u-pull-right"),
                    # ], className=""),
                    # html.Details([
                    #     html.Summary("Latest changes..."),
                    #     html.Div([
                    #         html.P(
                    #             "2019-03-19: Add Priority to run checker."),
                    #         html.P(
                    #             "2019-03-14: Add Supplying lab feedback option."),
                    #         html.P(
                    #             "2019-03-07: Add QC values to Run checker."),
                    #         html.P(
                    #             "2019-02-28: Add assemblatron links to sample folder generator. Only samples run from now on will have the right paths."),
                    #         html.P("2019-02-13: Filters default to empty (but behavior is the same), bring back apply button to reduce performance issues, add current run to run selector and other performance fixes. Add Latest changes section."),
                    #     ])
                    # ]),
                    # dcc.Store(id="data-store", storage_type="memory"),
                    # 
                    # html.Div(html_table([["run_name", ""]]), id="run-table"),
                    # html_div_summary(),
                    # html.Div(id="current-report"),
                    # html.Div(
                    #     [
                    #         html.H5(
                    #             [
                    #                 "Generate sample folder script"
                    #             ],
                    #             className="box-title"
                    #             ),
                    #         html.Div(
                    #             [
                    #                 html.Div(
                    #                     [
                    #                         html.Button(
                    #                             "Assembly/Sample folder",
                    #                             id="generate-folder",
                    #                             n_clicks_timestamp=0,
                    #                             className="button-primary u-full-width"
                    #                         )
                    #                     ],
                    #                     className="twelve columns"
                    #                 ),
                    #             ],
                    #             className="row"
                    #         ),
                    #         html.Div(
                    #             [
                    #                 html.Div(
                    #                     [
                    #                         html.Div(id="sample-folder-div")
                    #                     ],
                    #                     className="twelve columns"
                    #                 ),
                    #             ],
                    #             className="row",
                    #             style={"marginBottom": "15px"}
                    #         )
                    #     ],
                    #     className="border-box"
                    # ),
                    # These here avoid problems loading parameters when 
                    # loading a view other than the filter with params.
                    html.Button(id="apply-filter-button",
                               style={"display": "none"},
                               n_clicks=0),
                    dcc.Input(value="",
                              style={"display": "none"},
                              id="run-list"),
                    dcc.Input(value="",
                              style={"display": "none"},
                              id="species-list"),
                    dcc.Input(value="provided",
                              style={"display": "none"},
                              id="form-species-source"),
                    dcc.Input(value="",
                              style={"display": "none"},
                              id="group-list"),
                    dcc.Input(value="",
                              style={"display": "none"},
                              id="qc-list"),
                    dcc.Input(value="",
                              style={"display": "none"},
                              id="samples-form"),
                    html.Footer([
                        "Created with 🔬 at SSI. Bacteria icons from ",
                        html.A("Flaticon", href="https://www.flaticon.com/"),
                        "."], className="footer container")
                ], className="col-md-9 ml-sm-auto col-lg-10 px-4",
                role="main"),
        ]),
    ], className="appcontainer", fluid=True)
])


# Callbacks

# We could make this one much faster by hiding the unused species with CSS
# by adding a new hidden class.


@app.callback(
    [Output("selected-view", "children"),
     Output("param-store", "data")],
    [Input("url", "pathname")],
    [State("url", "search"),
     State("sample-store", "data")]
)
def update_run_name(pathname, params, sample_store):
    pparse = urlparse.urlparse(params)
    params = urlparse.parse_qs(pparse.query)

    if pathname is None or pathname == "/":
        pathname = "/"
    path = pathname.split("/")
    if path[1] == "":
        return [html_div_filter(), params]
    elif path[1] == "sample-report":
        return [sample_report(sample_store), params]
    elif path[1] == "pipeline-report":
        return [pipeline_report(sample_store), params]
    else:
        return ["Not found", params]


@app.callback(
    [Output("run-list", "options"),
     Output("group-list", "options"),
     Output("species-list", "options")],
    [Input("form-species-source", "value")]
)
def update_run_options(form_species):
    # Runs
    run_list = import_data.get_run_list()
    run_options = [
        {
            "label": "{} ({})".format(run["name"],
                                      len(run["samples"])),
            "value": run["name"]
        } for run in run_list]

    # Groups
    group_list = import_data.get_group_list()
    group_options = []
    for item in group_list:
        if item["_id"] is None:
            group_options.append({
                "label": "Not defined ({})".format(item["count"]),
                "value": "Not defined"
            })
        else:
            group_options.append({
                "label": "{} ({})".format(item["_id"], item["count"]),
                "value": item["_id"]
            })

    species_list = import_data.get_species_list(form_species)

    species_options = []
    for item in species_list:
        if item["_id"] == None:
            species_options.append({
                "label": "Not classified",
                "value": "Not classified"
            })
        else:
            species_options.append({
                "label": item["_id"],
                "value": item["_id"]
            })

    return [run_options, group_options, species_options]


@app.callback(
    [Output("run-list", "value"),
     Output("group-list", "value"),
     Output("species-list", "value"),
     Output("qc-list", "value"),
     Output("samples-form", "value")],
    [Input("param-store", "data")]
)
def update_filter_values(param_store):
    print(param_store)
    runs = param_store.get("run", [])
    groups = param_store.get("group", [])
    species = param_store.get("species", [])
    qcs = param_store.get("qc", [])
    sample_names = param_store.get("sample_names", [])
    return [runs, groups, species, qcs, "\n".join(sample_names)]

@app.callback(
    Output("lasso-div", "children"),
    [Input("summary-plot", "selectedData"),
     Input('datatable-ssi_stamper', 'derived_virtual_data'),
     Input('datatable-ssi_stamper', 'derived_virtual_selected_rows')]
)
def display_selected_data(selected_data, rows, selected_rows):
    # ignore_this is there so the function is called 
    # when the sample list is updated.
    if rows == [{}] or rows == [] or rows == None:
        return [
            html.Label(
                [
                    "Selected from table/lasso (0):"
                ],
                htmlFor="selected-from-plot"),
            dcc.Textarea(
                id="selected-from-plot",
                className="u-full-width",
                style={"resize": "none"},
                readOnly=True,
                value=""
            ),
            html.Div(style={"display": "none"},
                        id="lasso-sample-ids")
        ]
    dtdf = pd.DataFrame(rows)
    if selected_rows is not None and len(selected_rows) > 0:
        dtdf = dtdf.iloc[selected_rows]
    points = list(map(str, list(dtdf["name"])))
    sample_ids = list(dtdf["_id"])
    if selected_data is not None and len(selected_data["points"]):
        lasso_points = set([sample["text"]
                    for sample in selected_data["points"]])
        lasso_sample_ids = set([sample["customdata"]
                        for sample in selected_data["points"]])
        union_points = set(points).intersection(lasso_points)
        union_sample_ids = set(sample_ids).intersection(lasso_sample_ids)
        # This way we keep the table order.
        points = list(dtdf[dtdf["_id"].isin(lasso_sample_ids)]["name"])
        sample_ids = [sample_id for sample_id in sample_ids if sample_id in union_sample_ids]
    return [
        html.Label(
            [
                "Selected from table/lasso (",
                    str(len(points)),
                "):"
            ],
            htmlFor="selected-from-plot"),
        dcc.Textarea(
            id="selected-from-plot",
            className="u-full-width",
            style={"resize": "none"},
            readOnly=True,
            value=", ".join(points)
        ),
        html.Div(",".join(sample_ids),
                    style={"display": "none"},
                    id="lasso-sample-ids")
    ]





# @app.callback(
#     Output("run-table", "children"),
#     [Input("run-name", "children"),
#         Input("url", "pathname")]
# )
# def update_run_table(run_name, pathname):
#     if run_name == "Loading...":
#         return None
#     if pathname is None:
#         pathname = "/"
#     path = pathname.split("/")
#     if run_name == "Not found":
#         run = "Run not found!"
#     elif run_name == None or run_name == "":
#         run = "No run selected"
#     else:
#         run = run_name
#         year = run[:2]
#         run_path = keys.run_path + "20{}/{}".format(year, run_name)
#         run_link = "file:/" + run_path
#         if hasattr(keys, "path_platform_windows") and keys.path_platform_windows:
#             run_path = run_path.replace("/", "\\")
#         run_a=html.A(run_path, href=run_link)
#         run_checker_url = "{}/{}".format(keys.run_checker_url, run_name)
#         run_checker_link = html.A(run_checker_url, href=run_checker_url)
#         if len(path) > 2 and path[2] != "":
#             group = path[2]
#             return html_table([
#                 ["Run Name", run],
#                 ["Run Path", run_a],
#                 ["Supplying lab", group],
#                 ["Run Checker", run_checker_link]
#             ])
#         else:
#             return html_table([
#                 ["Run Name", run],
#                 ["Run Path", run_a],
#                 ["Run Checker", run_checker_link]
#             ])
#     return html_table([["Run Name", run]])

@app.callback(
    Output("page-n",
            "children"),
    [Input("prevpage", "n_clicks_timestamp"),
        Input("prevpage2", "n_clicks_timestamp"),
        Input("nextpage", "n_clicks_timestamp"),
        Input("nextpage2", "n_clicks_timestamp")],
    [State("page-n", "children"),
        State("max-page", "children")]
)
def next_page(prev_ts, prev_ts2, next_ts, next_ts2, page_n, max_page):
    page_n = int(page_n)
    max_page = int(max_page)
    if max(prev_ts, prev_ts2) > max(next_ts, next_ts2):
        return str(max(page_n - 1, 0))
    elif max(next_ts, next_ts2) > max(prev_ts, prev_ts2):
        return str(min(page_n + 1, max_page))
    else:
        return '0'


@app.callback(
    Output("sample-report", "children"),
    [Input("page-n", "children"),
     Input("sample-store", "data")]
        )
def fill_sample_report(page_n, sample_store):
    page_n = int(page_n)
    sample_ids = list(
        map(lambda x: x["_id"], sample_store))
    if len(sample_ids) == 0:
        return None
    
    data_table = import_data.filter_all(
        sample_ids=sample_ids,
        include_s_c=True,
        pagination={"page_size": SAMPLE_PAGESIZE, "current_page": page_n})
    max_page = len(sample_store) // SAMPLE_PAGESIZE
    # We need to have fake radio buttons with the same ids to account for times 
    # when not all SAMPLE_PAGESIZE samples are shown and are not taking the ids required by the callback
    html_fake_radio_buttons = html.Div([dcc.RadioItems(
        options=[
            {'label': '', 'value': 'nosample'}
        ],
        value='noaction',
        id="sample-radio-{}".format(n_sample)
    ) for n_sample in range(len(data_table), SAMPLE_PAGESIZE)], style={"display": "none"})
    return [
        html.H4("Page {} of {}".format(page_n + 1, max_page + 1)),
        html.Div(children_sample_list_report(data_table)),
        html_fake_radio_buttons,
        admin.html_qc_expert_form(),
        html.H4("Page {} of {}".format(page_n + 1, max_page + 1)),
        dcc.ConfirmDialog(
            id='qc-confirm',
            message='Are you sure you want to send sample feedback?',
        )
    ]

# @app.callback(
#     Output("sample-folder-div", "children"),
#     [
#         Input("generate-folder", "n_clicks_timestamp")],
#     [
#         State("lasso-sample-ids", "children"),
#         State("data-store", "data")]
# )
# def generate_sample_folder_div(n_generate_ts,
#                   lasso_selected, data_store):

#     if n_generate_ts == 0:
#         return None

#     if lasso_selected != "":
#         samples = lasso_selected.split(",")  # lasso first
#     elif data_store != None:
#         #json_data = StringIO(data_store)
#         samples = pd.DataFrame.from_dict(data_store)["_id"]
#     else:
#         samples = []

#     return generate_sample_folder(samples)


@app.callback(
    Output("current-report", "children"),
    [Input("lasso-sample-ids", "children")]
)

def update_report(lasso_selected):
    if lasso_selected is None or lasso_selected == "":
        return []
    else:
        sample_n = lasso_selected.count(",") + 1
        


@app.callback(
    [
     #Output("filter-sample-count", "children"),
     #Output("datatable-ssi_stamper", "data"),
     Output("sample-store", "data")],
    [Input("apply-filter-button", "n_clicks"),
     Input("param-store", "data")],
    [State("run-list", "value"),
     State("species-list", "value"),
     State("form-species-source", "value"),
     State("group-list", "value"),
     State("qc-list", "value"),
     State("samples-form", "value")]
)
def update_selected_samples(n_clicks, param_store,
                            run_names, species_list,
                            species_source, group_list, qc_list,
                            sample_names):

    if sample_names is not None and sample_names != "":
        sample_names = sample_names.split("\n")
    else:
        sample_names = param_store.get("sample_names", [])
    if not run_names:
        run_names = param_store.get("run", [])
    if not group_list:
        group_list = param_store.get("group", [])
    if not species_list:
        species_list = param_store.get("species", [])
    if not qc_list:
        qc_list = param_store.get("qc", [])
        

    if (n_clicks == 0 and
        sample_names == [] and
        run_names == [] and
        group_list == [] and
        species_list == [] and
        qc_list == []):
        raise InterruptedError

    samples = import_data.filter_all(
        species=species_list, species_source=species_source,
        group=group_list, qc_list=qc_list,
        run_names=run_names,
        sample_names=sample_names,
        include_s_c=False,
        projection={"name": 1})

    samples["_id"] = samples["_id"].astype(str)
    samples = samples.to_dict('records')

    return [samples]



@app.callback(
    [Output("filter-sample-count", "children"),
     Output("datatable-ssi_stamper", "data")],
    [Input("sample-store", "data"),
     Input('datatable-ssi_stamper', 'pagination_settings')]
)
def update_filter_table(sample_store, pagination_settings):
    if len(sample_store) == 0:
        return ["0", [{}]]
    sample_ids = list(
        map(lambda x: x["_id"], sample_store))

    samples = import_data.filter_all(
        sample_ids=sample_ids,
        pagination=pagination_settings,
        include_s_c=True)

    samples = generate_table(samples)
    return [len(sample_store), samples.to_dict("rows")]
    # return [sample_count, tests_df.to_dict("rows"), samples]


@app.callback(
    Output("tsv-download", "children"),
    [Input("generate-download-button", "n_clicks")],
    [State("run-list", "value"),
     State("species-list", "value"),
     State("form-species-source", "value"),
     State("group-list", "value"),
     State("qc-list", "value"),
     State("samples-form", "value")]
)
def generate_download_button(download_button,
                            run_names, species_list,
                            species_source, group_list, qc_list,
                            sample_names):
    if download_button == 0:
        return None
    else:
        if sample_names is not None and sample_names != "":
            sample_names = sample_names.split("\n")

        tests_df, query_count = import_data.filter_all(species=species_list, species_source=species_source,
                                                       group=group_list, qc_list=qc_list,
                                                       run_names=run_names,
                                                       sample_names=sample_names,
                                                       pagination=None)
    # return samples.to_dict()
    if query_count == 0:
        return None

    tests_df = generate_table(tests_df)

    rename_dict = {item["id"]: item["name"]
        for item in global_vars.COLUMNS}

    renamed = tests_df.rename(rename_dict, axis='columns')

    missing_columns = [a for a in list(
        rename_dict.values()) if not a in list(renamed.columns)]

    # add missing columns
    for column in missing_columns:
        renamed[column] = np.nan

    # reorder columns
    renamed = renamed[list(rename_dict.values())]

    csv_string_eur = renamed.to_csv(
        index=False, encoding="utf-8", sep=";", decimal=",")
    tsv_string_us = renamed.to_csv(index=False, encoding="utf-8", sep="\t")
    full_csv_string_eur = 'data:text/csv;charset=utf-8,' + \
        urlparse.quote(csv_string_eur)
    full_tsv_string_us = 'data:text/tab-separated-values;charset=utf-8,' + \
        urlparse.quote(tsv_string_us)
    return [
        html.A("(tsv, US format)",
                href=full_tsv_string_us,
                download='report.tsv'),
        " - ",
        html.A("(csv, EUR Excel format)",
                href=full_csv_string_eur,
                download='report.csv')
    ]

# @app.callback(
#     Output("sample-store", "data"),
#     [Input("save-samples-button", "n_clicks")],
#     [State("sample-store", "data"),
#      State("run-list", "value"),
#      State("species-list", "value"),
#      State("form-species-source", "value"),
#      State("group-list", "value"),
#      State("qc-list", "value"),
#      State("samples-form", "value")]
# )
# def select_samples(n_clicks, sample_store, run_names, species_list,
#                    species_source, group_list, qc_list,
#                    sample_names):
    
#     else:
#         tests_df, query_count = import_data.filter_all(species=species_list,
#             species_source=species_source,
#             group=group_list,
#             qc_list=qc_list,
#             run_names=run_names,
#             sample_names=sample_names,
#             pagination=None,
#             projection={"name": 1})
#     tests_df["_id"] = tests_df["_id"].astype(str)
#     sample_store["selected_samples"] = tests_df.to_dict('records')
#     return sample_store


@app.callback(
    Output("selected-samples", "children"),
    [Input("sample-store", "data")]
)
def store_update(sample_store):
    rows = []
    for sample in sample_store[:500]:
        rows.append(html.Tr(html.Td(sample["name"])))
    if len(sample_store) > 500:
        rows.append(html.Tr(html.Td(
            "{} more samples".format(len(sample_store) - 500))))
    return html.Tbody(rows)



@app.callback(
    Output("plot-species-div", "children"),
    [Input('datatable-ssi_stamper', 'derived_virtual_data'),
     Input('datatable-ssi_stamper', 'derived_virtual_selected_rows'),
     Input("plot-species-source", "value")],
    [State("plot-species", "value")]
)
def plot_species_dropdown(rows, selected_rows, plot_species, selected_species):
    plot_df = pd.DataFrame(rows)
    if selected_rows is not None and len(selected_rows) > 0:
        plot_df = plot_df.iloc[selected_rows]
    # part of the HACK, replace with "properties.detected_species" when issue is solved
    species_col = "properties_detected_species"

    if plot_species == "provided":
        species_col = "properties_provided_species"
    elif plot_species == "detected":
        species_col = "properties_detected_species"
    # end HACK
    if species_col not in plot_df or plot_df[species_col].unique() is None:
        return dcc.Dropdown(
            id="plot-species"
        )
    plot_df.loc[pd.isnull(plot_df[species_col]), species_col] = "Not classified"
    species_list = plot_df[species_col].unique()
    species_list = ["All species",] + list(species_list)
    if selected_species == "Not classified" or selected_species is None or selected_species not in species_list:
        if species_list[0] == "Not classified" and len(species_list) > 1:
            selected_species = species_list[1]
        else:
            selected_species = species_list[0]
    species_list_options = [
        {
            "label": species,
            "value": species
        } for species in species_list]
    return dcc.Dropdown(
        id="plot-species",
        options=species_list_options,
        value=selected_species
    )


# @app.callback(
#     Output("summary-plot", "selectedData"),
#     [Input("data-store", "data"),
#      Input("plot-species", "value"),
#      Input('datatable-ssi_stamper', 'derived_virtual_data'),
#      Input('datatable-ssi_stamper', 'derived_virtual_selected_rows')]
# )
# def reset_selection(sample_ids, plot_value, rows, selected_rows):
#     return {"points":[]}


# @app.callback(
#     Output("summary-plot", "figure"),
#     [Input("plot-species", "value"),
#      Input('datatable-ssi_stamper', 'derived_virtual_data'),
#      Input('datatable-ssi_stamper', 'derived_virtual_selected_rows')],
#     [State("plot-species-source", "value")]
# )
# def update_coverage_figure(selected_species, rows, selected_rows, plot_species_source):
#     if rows == [{}] or rows == [] or rows == None:
#         return {"data":[]}
#     plot_values = global_vars.plot_values
#     traces = []
#     trace_ranges = []

#      # part of the HACK, replace with "properties.detected_species" when issue is solved
#     species_col = "properties_detected_species"
#     if plot_species_source == "provided":
#         species_col = "properties_provided_species"
#     elif plot_species_source == "detected":
#         species_col = "properties_detected_species"
#     # end HACK

#     plot_df = pd.DataFrame(rows)
#     if selected_rows is not None and len(selected_rows) > 0:
#         plot_df = plot_df.iloc[selected_rows]
#     plot_df.loc[pd.isnull(plot_df[species_col]),
#                 species_col] = "Not classified"

#     df_ids = plot_df["_id"]
#     if species_col in plot_df.columns and (selected_species in plot_df[species_col].unique() or
#         selected_species == "All species"):
#         for plot_value in plot_values:
#             plot_id = plot_value["id"].replace(".", "_").replace(":", "_")  #HACK
#             if selected_species == "All species":
#                 species_df = plot_df
#             else:
#                 species_df = plot_df[plot_df[species_col] == selected_species]
#             species_df[plot_id] = pd.to_numeric(species_df[plot_id], errors="coerce")
#             if (plot_id in species_df.columns):
#                 data_range = plot_value["limits"][1] - plot_value["limits"][0]
#                 low_limit = min(float(species_df[plot_id].min()), plot_value["limits"][0])
#                 if low_limit == float(species_df[plot_id].min()):
#                     low_limit -= data_range * 0.1
#                 high_limit = max(float(species_df[plot_id].max()), plot_value["limits"][1])
#                 if high_limit == float(species_df[plot_id].max()):
#                     high_limit += data_range*0.1
#                 trace_ranges.append([low_limit, high_limit])
#                 traces.append(
#                     go.Box(
#                         x=species_df.loc[:, plot_id],
#                         text=species_df["name"],
#                         marker=dict(
#                             size=4
#                         ),
                        
#                         boxpoints="all",
#                         jitter=0.3,
#                         pointpos=-1.6,
#                         selectedpoints=list(
#                             range(len(species_df.index))),
#                         name=plot_value["name"],
#                         showlegend=False,
#                         customdata=species_df["_id"]
#                     )
#                 )
#     fig = tools.make_subplots(rows=7, cols=1, print_grid=False)
#     fig["layout"].update(
#         hovermode="closest",
#         title=selected_species,
#         height=750,
#         margin=go.layout.Margin(
#             l=175,
#             r=50,
#             b=25,
#             t=50
#         ),
#     )
#     try:
#         fig.append_trace(traces[0], 1, 1)
#         fig.append_trace(traces[1], 1, 1)
#         fig.append_trace(traces[2], 2, 1)
#         fig.append_trace(traces[3], 3, 1)
#         fig.append_trace(traces[4], 4, 1)
#         fig.append_trace(traces[5], 5, 1)
#         fig.append_trace(traces[6], 6, 1)
#         fig.append_trace(traces[7], 7, 1)
        
#         fig["layout"]["xaxis"].update(range=trace_ranges[0])
#         fig["layout"]["xaxis2"].update(range=trace_ranges[2])
#         fig["layout"]["xaxis3"].update(range=trace_ranges[3])
#         fig["layout"]["xaxis4"].update(range=trace_ranges[4])
#         fig["layout"]["xaxis5"].update(range=trace_ranges[5])
#         fig["layout"]["xaxis6"].update(range=trace_ranges[6])
#         fig["layout"]["xaxis7"].update(range=trace_ranges[7])
#     except IndexError:
#         pass # It won't draw al ranges/traces because they don't exist.


#     fig["layout"]["yaxis"].update(domain=(0.78,1))
#     fig["layout"]["yaxis2"].update(domain=(0.655, 0.75))
#     fig["layout"]["yaxis3"].update(domain=(0.53, 0.625))
#     fig["layout"]["yaxis4"].update(domain=(0.415, 0.5))
#     fig["layout"]["yaxis5"].update(domain=(0.28, 0.375))
#     fig["layout"]["yaxis6"].update(domain=(0.155, 0.25))
#     fig["layout"]["yaxis7"].update(domain=(0.03, 0.125))

#     species_size = import_data.get_species_QC_values(selected_species)
#     if species_size is None:
#         species_size = import_data.get_species_QC_values("default")

#     annotations = [
#         {
#             "x": species_size["min_length"],
#             "y": 0,
#             "xref": "x",
#             "yref": "y",
#             "text": "min",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {
#             "x": species_size["min_length"],
#             "y": 1,
#             "xref": "x",
#             "yref": "y",
#             "text": "min",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {
#             "x": species_size["max_length"],
#             "y": 0,
#             "xref": "x",
#             "yref": "y",
#             "text": "max",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {
#             "x": species_size["max_length"],
#             "y": 1,
#             "xref": "x",
#             "yref": "y",
#             "text": "max",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {
#             "x": 250000,
#             "y": 0,
#             "xref": "x2",
#             "yref": "y2",
#             "text": "max",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         { # Cov
#             "x": 10,
#             "y": 0,
#             "xref": "x3",
#             "yref": "y3",
#             "text": "fail",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         { # Cov
#             "x": 25,
#             "y": 0,
#             "xref": "x3",
#             "yref": "y3",
#             "text": "low",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         { # Cov
#             "x": 50,
#             "y": 0,
#             "xref": "x3",
#             "yref": "y3",
#             "text": "warn",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         { # Num reads
#             "x": 10000,
#             "y": 0,
#             "xref": "x5",
#             "yref": "y5",
#             "text": "min",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {  # Main+uncl
#             "x": 0.95,
#             "y": 0,
#             "xref": "x6",
#             "yref": "y6",
#             "text": "min",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#         {  # Uncl
#             "x": 0.2,
#             "y": 0,
#             "xref": "x7",
#             "yref": "y7",
#             "text": "max",
#             "arrowhead": 0,
#             "ax": 0,
#             "ay": 40
#         },
#     ]

#     fig["layout"].update(annotations=annotations)
#     return fig


def create_stamp(value, user):
    return {
        "name": "supplying_lab_check",
        "user-ip": str(request.remote_addr),
        "user": user,
        "date": datetime.datetime.utcnow(),
        "value": value
    }


#  

@app.callback(Output('qc-confirm', 'displayed'),
              [Input('feedback-button', 'n_clicks_timestamp')])
def display_confirm_feedback(button):
    if button is not None:
        return True
    return False


@app.callback(
    Output("placeholder0", "children"),
    [Input("qc-confirm", "submit_n_clicks")],
    [State("qc-user-1", "value")] + [State("sample-radio-{}".format(n), "value")
                                     for n in range(SAMPLE_PAGESIZE)]
)
def print_radio(n_clicks_timestamp, user, *args):
    if ("REPORTER_ADMIN" in os.environ and os.environ["REPORTER_ADMIN"] == "True"):
        stamp_a = create_stamp("pass:accepted", user)
        stamp_r = create_stamp("fail:resequence", user)
        stamp_o = create_stamp("fail:other", user)
        stamplist = []
        for val in args:
            if val != "noaction":
                if val.startswith("A_"):
                    stamplist.append((val[2:], stamp_a))
                elif val.startswith("R_"):
                    stamplist.append((val[2:], stamp_r))
                elif val.startswith("O_"):
                    stamplist.append((val[2:], stamp_o))
        if len(stamplist) > 0:
            import_data.email_stamps(stamplist)
            import_data.post_stamps(stamplist)
    return []


server = app.server # Required for gunicorn

if __name__ == '__main__':
    # 0.0.0.0 exposes the app to the network.
    app.run_server(debug=True, host="0.0.0.0", dev_tools_hot_reload=True)
