# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import urllib.parse as urlparse

import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import plotly.figure_factory as ff
from dash.dependencies import Input, Output, State
import keys

import dash_scroll_up

import components.import_data as import_data

import json
from bson import json_util



def pipeline_report(sample_data):
    update_notice = "The table will update every 30s automatically."


    table = dash_table.DataTable(
        id="pipeline-table", selected_rows=[],
        style_table={
            'overflowX': 'scroll',
            'width': '100%'
        },
        page_action='none',
        style_as_list_view=True,
        style_cell={
            'textAlign': 'center',
            "fontFamily": "Arial",
            "padding": "0px 10px",
            "fontSize": "0.7rem",
            "height": "25px"
            })

    update_notice += (" Req.: requirements not met. Init.: initialised. "
                      "*: user submitted")
    rerun_columns = [
        {"id": "sample", "name": "sample"},
        {"id": "component", "name": "component"},
    ]

    return [
        # resequence_link,
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Div([
                        html.H6("Pipeline status", className="m-0 font-weight-bold text-primary")
                    ], className="card-header py-3"),
                    html.Div([
                        html.P(update_notice),
                        table,
                        dcc.Interval(
                            id='table-interval',
                            interval=30*1000,  # in milliseconds
                            n_intervals=0
                        )
                    ], className="card-body")
                ], className="card shadow mb-4")                
            ], width=9),
            dbc.Col([
                html.Div([
                    html.Div([
                        html.H6("Rerun components",
                                className="m-0 font-weight-bold text-primary")
                    ], className="card-header py-3"),
                    html.Div([
                        dbc.Alert(id="rerun-output",
                                  color="secondary",
                                  dismissable=True,
                                  is_open=False),
                        html.Label(html.Strong(
                            "Add all components for sample")),
                        dbc.InputGroup([
                            dcc.Dropdown(id="rerun-components",
                                         className="dropdown-group"),
                            dbc.InputGroupAddon(
                                dbc.Button("Add", id="rerun-add-components"),
                                addon_type="append",
                            ),
                        ]),
                        html.Label(html.Strong("Add component for all samples"),
                                   className="mt-3"),
                        dbc.InputGroup([
                            dcc.Dropdown(id="rerun-samples",
                                         className="dropdown-group"),
                            dbc.InputGroupAddon(
                                dbc.Button("Add", id="rerun-add-samples"),
                                addon_type="append",
                            ),
                        ]),
                        html.Label(html.Strong("Add all failed components"),
                                   className="mt-3"),
                        dbc.Button("Add", id="rerun-add-failed", block=True),
                        html.Div([
                            html.H4("Selected sample components"),
                            dash_table.DataTable(
                                id="pipeline-rerun",
                                columns=rerun_columns,
                                row_deletable=True),
                            dbc.Button("Rerun selected sample components",
                                       id="rerun-button", className="mt-3", block=True,
                                       color="primary"),
                        ], className="mt-3")
                    ], className="card-body")
                ], className="card shadow mb-4")
            ], width=3
            )
        ])
    ]


def pipeline_report_data(sample_data):

    status_dict = {
        "Success": "OK",
        "Running": "Running",
        "initialized": "init.",
        "Failure": "Fail",
        "Requirements not met": "Req.",
        "queued to run": "queue",
    }
    samples = import_data.filter_all(
        sample_ids = [s["_id"] for s in sample_data],
        include_s_c=False,
        projection={"stamps": 1, 'name': 1, 'sample_sheet.priority': 1})
    samples["_id"] = samples["_id"].astype(str)
    samples = samples.set_index("_id")

    s_c_status = import_data.get_sample_component_status(
        sample_data)

    components_order = [
        "whats_my_species", "analyzer", "assemblatron", "ssi_stamper",
        "ariba_resfinder", "ariba_mlst", "ariba_plasmidfinder",
        "ariba_virulencefinder", "sp_cdiff_fbi", "sp_ecoli_fbi",
        "sp_salm_fbi", "min_read_check", "qcquickie"]


    s_c_components = []
    for sample in s_c_status:
        for comp_name in sample['s_cs'].keys():
            if comp_name not in s_c_components:
                s_c_components.append(comp_name)
    components_list = [comp for comp in components_order if comp in s_c_components]

    rows = []

    columns = [
        {"name": "Priority", "id": "priority"},
        {"name": "Sample", "id": "sample"},
        {"name": "QC status", "id": "qc_val"}
    ]

    rerun_form_components = []

    for comp in components_list:
        columns.append({"name": comp, "id": comp})
        rerun_form_components.append({"label": comp, "value": comp})

    # Conditional data colors
    style_data_conditional = [
        {
            "if": {
                "column_id": "qc_val",
                "filter_query": '{qc_val} contains "CF"'
            },
            "backgroundColor": "#ea6153"
        },
        {
            "if": {
                "column_id": "qc_val",
                "filter_query": '{qc_val} contains "CF(LF)"'
            },
            "backgroundColor": "#ea6153"
        },
        {
            "if": {
                "column_id": "qc_val",
                "filter_query": '{qc_val} contains "OK"'
            },
            "backgroundColor": "#27ae60"
        },
        {
            "if": {
                "column_id": "qc_val",
                "filter_query": '{qc_val} eq "SL"'
            },
            "backgroundColor": "#f1c40f"
        }
    ]
    for col in s_c_components:
        style_data_conditional.append({
            "if": {
                "column_id": col,
                "filter_query": '{{{}}} eq "Fail"'.format(col)
            },
            "backgroundColor": "#ea6153"
        })
        style_data_conditional.append({
            "if": {
                "column_id": col,
                "filter_query": '{{{}}} eq "OK"'.format(col)
            },
            "backgroundColor": "#3498db"
        })
        style_data_conditional.append({
            "if": {
                "column_id": col,
                "filter_query": '{{{}}} eq "Running"'.format(col)
            },
            "backgroundColor": "#f1c40f"
        })
        style_data_conditional.append({
            "if": {
                "column_id": col,
                "filter_query": '{{{}}} eq "Req."'.format(col)
            },
            "backgroundColor": "#d3d3d3",
            "color": "#525252"
        })

    rerun_form_samples = []

    for s_components in s_c_status:
        sample_id = str(s_components["_id"])
        sample = samples.loc[sample_id]
        name = sample["name"]

        row = {}
        if name == "Undetermined":
            continue  # ignore this row

        row["sample"] = name
        row["_id"] = sample_id

        rerun_form_samples.append({"label": name, "value": "{}:{}".format(
            sample_id, name)})

        priority = str(sample.get("sample_sheet.priority", "")).lower()
        # prio_display = " " Emoji not supported
        # if priority == "high":
        #     prio_display = "High"
        # else:
        #     prio_display = "Low"
        row["priority"] = priority
        qc_val = sample.get("stamps.ssi_stamper.value", "N/A")
        if pd.isna(qc_val):
            qc_val = "N/A"

        expert_check = False
        expert_stamp = sample.get('stamps.supplying_lab_check.value')
        if expert_stamp is not None and not pd.isna(expert_stamp):
            qc_val = sample.get('stamps.supplying_lab_check.value')
            expert_check = True

        statusname = ""
        if qc_val == "fail:supplying lab":
            qc_val = "SL"
            statusname = "status-1"
        elif qc_val == "N/A":
            statusname = "status--2"
        elif (qc_val == "fail:core facility" or
                qc_val == "fail:resequence"):
            statusname = "status--1"
            qc_val = "CF"
        elif qc_val == "pass:OK" or qc_val == "pass:accepted":
            statusname = "status-2"
            qc_val = "OK"

        if expert_check:
            try:
                qc_val += "*"
            except:
                print(sample)

        row["qc_val"] = qc_val

        for component in components_list:
            if component in s_components["s_cs"].keys():
                s_c = s_components["s_cs"][component]
                row[component] = status_dict[s_c]
            else:
                row[component] = "None"
        rows.append(row)
    def sort_name(e):
        return e["sample"]
    rows.sort(key=sort_name)
    return rows, columns, style_data_conditional, rerun_form_components, rerun_form_samples





def rerun_components_button(button, table_data):
    if button == 0:
        return "", False
    out = []
    to_rerun = {}
    for row in table_data:
        sample_rerun = to_rerun.get(row["sample_id"], [])
        sample_rerun.append(row["component"])
        to_rerun[row["sample_id"]] = sample_rerun
    
    sample_dbs = import_data.get_samples(sample_ids=to_rerun.keys())
    samples_by_id = {str(s["_id"]) : s for s in sample_dbs}

    bifrost_components_dir = os.path.join(keys.rerun["bifrost_dir"], "components/")

    for sample, components in to_rerun.items():
        sample_db = samples_by_id[sample]
        sample_name = sample_db["name"]
        run_path = sample_db["path"]
        sample_command = ""
        for component in components:
            component_path = os.path.join(bifrost_components_dir,
                                          component, "pipeline.smk")
            command = r'if [ -d \"{}\" ]; then rm -r {}; fi; '.format(
                component, component)
            # unlock first
            command += (r"snakemake --shadow-prefix /scratch --restart-times 2"
                        r" --cores 4 -s {} "
                        r"--config Sample=sample.yaml --unlock; ").format(
                            component_path)
            command += (r"snakemake --shadow-prefix /scratch --restart-times 2"
                        r" --cores 4 -s {} "
                        r"--config Sample=sample.yaml; ").format(
                            component_path)
            sample_command += command
        
        if keys.rerun["grid"] == "slurm":
            process = subprocess.Popen(
                ('sbatch --mem={memory}G -p {priority} -c {threads} '
                    '-t {walltime} -J "bifrost_{sample_name}" --wrap'
                    ' "{command}"').format(
                        **keys.rerun,
                        sample_name=sample_name,
                        command=sample_command),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
                env=os.environ,
                cwd=run_path)
            process_out, process_err = process.communicate()
            out.append((sample_name, process_out, process_err))
        elif keys.rerun["grid"] == "torque":

            if "advres" in keys.rerun:
                advres = ",advres={}".format(
                    keys.rerun["advres"])
            else:
                advres = ''
            torque_node = ",nodes=1:ppn={}".format(keys.rerun["threads"])
            script_path = os.path.join(run_path, "manual_rerun.sh")
            with open(script_path, "w") as script:
                command += ("#PBS -V -d . -w . -l mem={memory}gb,nodes=1:"
                            "ppn={threads},walltime={walltime}{advres} -N "
                            "'bifrost_{sample_name}' -W group_list={group}"
                            " -A {group} \n").format(**keys.rerun,
                                                     sample_name=sample_name)
                script.write(command)
            process = subprocess.Popen('qsub {}'.format(script_path),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT,
                                        shell=True,
                                        env=os.environ,
                                        cwd=run_path)
            process_out, process_err = process.communicate()
            out.append((sample_name, process_out, process_err))
        elif keys.rerun["grid"] == "slurm.mock":
            print(('sbatch --mem={memory}G -p {priority} -c {threads} '
                  '-t {walltime} -J "bifrost_{sample_name}" --wrap'
                  ' "{command}"').format(
                **keys.rerun,
                sample_name=sample_name,
                command=sample_command))

    message = "Jobs sent to the server:\n"
    message += "\n".join(["{}: out: {} | err: {}".format(*el)
                         for el in out])
    return message, True


def update_rerun_table(active, table_data, n_click_comp, n_click_samp,
                       n_click_fail, columns, prev_data, rerun_comp,
                       rerun_samp):
    # default values
    if prev_data is None:
        prev_data = []

    if columns:
        columns = columns[3:]

    #Get context to know which button was triggered.
    ctx = dash.callback_context

    if not ctx.triggered:
        triggered_id = None
    else:
        triggered_id = ctx.triggered[0]['prop_id']

    #Nothing triggered it, return empty table if init call or prev data.
    if active is None and triggered_id is None:
        return prev_data

    if triggered_id == "pipeline-table.active_cell":
        col = active["column_id"]
        sample = table_data[active["row"]]["sample"]
        sample_id = table_data[active["row"]]["_id"]

        new_rows = [{"sample": sample, "component": col,
                     "sample_id": sample_id}]
    elif triggered_id == "rerun-add-components.n_clicks":
        sample_id, sample = rerun_comp.split(":")
        new_rows = [{"sample": sample,
                     "component": comp["id"],
                     "sample_id": sample_id} for comp in columns]
    elif triggered_id == "rerun-add-samples.n_clicks":
        new_rows = []
        for row in table_data:
            new_rows.append({"sample": row["sample"],
                             "component": rerun_samp,
                             "sample_id": row["_id"]})
    elif triggered_id == "rerun-add-failed.n_clicks":
        new_rows = []
        for row in table_data:
            for col in columns:
                col = col["id"]
                if row[col] == "Fail":
                    new_rows.append({"sample": row["sample"],
                                     "component": col,
                                     "sample_id": row["_id"]})
    else:
        new_rows = []

    for new_row in new_rows:
        if new_row not in prev_data:
            prev_data = prev_data + [new_row]

    return prev_data
