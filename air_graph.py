import os
import math

import numpy as np
import networkx as nx
import holoviews as hv
from bokeh.io import curdoc
from bokeh.models import Circle, Slider, FuncTickFormatter, \
    HoverTool, TapTool, MultiLine, NodesAndLinkedEdges, ColorBar, \
    BasicTicker, LinearColorMapper, ColumnDataSource, Grid, HBar, LinearAxis, Plot, Select
from bokeh.models.annotations import Title
from bokeh.plotting import figure, show
from bokeh.layouts import gridplot
from bokeh.sampledata.us_states import data as states
from holoviews.operation.datashader import bundle_graph
hv.extension('bokeh')

############################################# Holoviews ################################################################

# Data preparation
graph_file_path = os.path.join(os.path.dirname(__file__), 'airlines.graphml')
G = nx.read_graphml(graph_file_path, node_type=int)

pos = dict()
node_and_x = nx.get_node_attributes(G, 'x')
node_and_y = nx.get_node_attributes(G, 'y')

labels = dict()
node_and_description = nx.get_node_attributes(G, 'tooltip')

codes = dict()

for i in range(G.number_of_nodes()):
    x = node_and_x[i]
    y = node_and_y[i]
    pos[i] = (x / 10, -y / 10)
    labels[i] = node_and_description[i].split('(')[0]
    codes[i] = {'code': node_and_description[i].split('(')[0]}

labels_arr = list(dict(labels).values())

# Graph creation
H = nx.Graph()
H.add_nodes_from(G.nodes())
H.add_edges_from(G.edges())
nx.set_node_attributes(H, codes)

degrees_arr = list(dict(H.degree).values())
min_size = min(degrees_arr)
max_size = max(degrees_arr)

hv_graph = hv.Graph.from_networkx(H, pos)
bundled_graph = bundle_graph(hv_graph, initial_bandwidth=0.04, decay=0.2, advect_iterations=10, batch_size=15,
                             tension=0.8)

# Map creation
map = figure(title=Title(text="Flights network"), plot_width=900)

map.xaxis.visible = False
map.yaxis.visible = False
map.xgrid.visible = False
map.ygrid.visible = False

if "HI" in states.keys() and "AK" in states.keys():
    del states["HI"]
    del states["AK"]

state_xs = [states[code]["lons"] for code in states]
state_ys = [states[code]["lats"] for code in states]

map.patches(state_xs, state_ys, fill_alpha=0.05, fill_color="lightblue",
            line_color="lightblue", line_width=2, line_alpha=0.25)

graph = hv.render(bundled_graph).renderers[0]

map_source = graph.node_renderer.data_source

map_source.data['colors'] = degrees_arr
map_source.data['labels'] = labels_arr
map_source.data['line_colors'] = ['#c6c6c6' for i in range(H.number_of_nodes())]
map_source.data['alpha'] = [1 for i in range(H.number_of_nodes())]
map_source.data['sizes'] = [10 for i in range(H.number_of_nodes())]

color_mapper = LinearColorMapper(palette='Viridis256', low=min_size, high=max_size)

graph.node_renderer.glyph = Circle(size='sizes', fill_color={'field': 'colors', 'transform': color_mapper},
                                   line_color='line_colors', fill_alpha='alpha', line_alpha="alpha")
graph.edge_renderer.glyph = MultiLine(line_color='#c6c6c6', line_alpha=1.0, line_width=0.25)

########################################## Map interaction #############################################################

# Hover tooltip
node_hover_tool = HoverTool(tooltips=[("Airport code", "@labels"), ("Num. of flights", "@colors")],
                            renderers=[graph.node_renderer])
map.add_tools(node_hover_tool, TapTool())

# Node selection
graph.node_renderer.selection_glyph = Circle(size='sizes', fill_color={'field': 'colors', 'transform': color_mapper},
                                             line_color='line_colors', fill_alpha='alpha', line_alpha="alpha")
graph.node_renderer.nonselection_glyph = Circle(size='sizes', fill_color={'field': 'colors', 'transform': color_mapper},
                                             line_color='line_colors', fill_alpha='alpha', line_alpha="alpha")
graph.node_renderer.hover_glyph = Circle(size='sizes', fill_color={'field': 'colors', 'transform': color_mapper})

graph.edge_renderer.selection_glyph = MultiLine(line_color='black', line_alpha=1, line_width=2.5)
graph.edge_renderer.nonselection_glyph = MultiLine(line_color='#c6c6c6', line_alpha=.5, line_width=0.25)


graph.selection_policy = NodesAndLinkedEdges()

# Legend under map
color_bar = ColorBar(color_mapper=color_mapper, ticker=BasicTicker(), title="Airport size (number of flights)",
                     location=(0, 0), orientation="horizontal")

map.add_layout(color_bar, 'below')

# Renderer
map.renderers.append(graph)
map.sizing_mode = 'scale_height'

####################################### Barchart #######################################################################

# Data preparation
sorted_tuple_list = sorted(zip(degrees_arr, labels_arr), key=lambda item: item[0], reverse=False)

degrees_sort_arr = [item[0] for item in sorted_tuple_list]
labels_sort_arr = [item[1] for item in sorted_tuple_list]

N = max_size - min_size
y = np.linspace(1, len(degrees_sort_arr), len(degrees_sort_arr))

# Barchart creation
source = ColumnDataSource(data=dict(y=y, right=degrees_sort_arr, colors=[v for v in degrees_sort_arr],
                                    labels=[v for v in labels_sort_arr]))

bar = Plot(title=Title(text="Airport size"), plot_width=500, plot_height=800, min_border=0)

glyph = HBar(y="y", right="right", left=0, fill_color={'field': 'colors', 'transform': color_mapper},
             line_width=1, height=0.98)
bar.add_glyph(source, glyph)

xaxis = LinearAxis()
bar.add_layout(xaxis, 'below')

yaxis = LinearAxis()
bar.add_layout(yaxis, 'left')

label_dict = {}
i = 1
for label in labels_sort_arr:
    label_dict[i] = label
    i = i + 1

bar.yaxis.formatter = FuncTickFormatter(code="""
    var labels = %s;
    return labels[tick];
""" % label_dict)

bar.xaxis.axis_label = 'Airport size (number of flights)'
bar.yaxis.axis_label = 'Airport code'

bar.add_layout(Grid(dimension=0, ticker=xaxis.ticker))
bar.add_layout(Grid(dimension=1, ticker=yaxis.ticker))

bar.yaxis.ticker = list(range(1, 236))
bar.sizing_mode = 'scale_height'

# Hover tooltip
hover_tool = HoverTool(tooltips=[("Airport code", "@labels"), ("Num. of flights", "@colors")])
bar.add_tools(hover_tool, TapTool())

#################################### Airport select dropdown ###########################################################
labels_a = [a for a in labels_sort_arr]
labels_a.sort()
labels_a.insert(0, '-')
select = Select(title="Airport code", value=labels_a[0], options=labels_a)

########################################## Sliders #####################################################################
bar.y_range.update(start=len(degrees_sort_arr) - 30 + .5, end=len(degrees_sort_arr) + .5)

# showing min. 30 and max. 100 items
count_slider = Slider(start=30, end=80, value=30, step=5, title="Show airports (count)")

# default count of airports shown = 30
scroll_slider = Slider(start=1, end=math.ceil((len(degrees_sort_arr) / 30) * 2), value=1, step=1, title="",
                       orientation="vertical")

###################################### Graph toggle - nesmysl ##########################################################
# toggle = Toggle(label="Bundle edges", button_type="success", align='end', width=100)
#
# def toggle_update(attrname, old, new):
#     if(toggle.active == True):
#         graph.layout_provider = hv.render(bundled_graph).renderers[0].layout_provider
#
#     else:
#         graph.layout_provider = hv.render(hv_graph).renderers[0].layout_provider
#
# toggle.on_change('active', toggle_update)

####################################### Scrolling the barchart #########################################################
scroll_values = list()
scroll_values.append(scroll_slider.value)


def scroll_update(attrname, old, new):
    shift = (scroll_slider.value - scroll_values.pop(0)) * count_slider.value / 2
    scroll_values.append(scroll_slider.value)
    bar.y_range.update(start=bar.y_range.start - shift, end=bar.y_range.end - shift)


scroll_slider.on_change('value', scroll_update)


########################################### Count of showing airports ##################################################
def count_update(attrname, old, new):
    a = count_slider.value
    shift = a - (bar.y_range.end - bar.y_range.start)

    scroll_slider.value = 1
    scroll_slider.end = math.ceil(len(degrees_sort_arr) / a * 2)
    bar.y_range.update(start=bar.y_range.start - shift, end=len(degrees_sort_arr) + .5)


count_slider.on_change('value', count_update)


########################################## Node selection ##############################################################
def selected_node(attrname, old, new):
    if len(graph.node_renderer.data_source.selected.indices) == 1:
        node_index = graph.node_renderer.data_source.selected.indices[0]
        node_label = labels[node_index]
        label_index = labels_sort_arr.index(node_label)

        # scroll
        scroll_slider.value = math.ceil(((len(degrees_sort_arr) - label_index) / count_slider.value) * 2)

        # highlight bar
        bar.renderers[0].data_source.selected.indices = [label_index]

        # highlight nodes
        neighbors = [n for n in nx.neighbors(H, node_index)]
        neighbors.append(node_index)  # add source node
        line_cols = ['#c6c6c6' for i in range(H.number_of_nodes())]
        alpha = [.5 for i in range(H.number_of_nodes())]
        for i in neighbors:
            line_cols[i] = 'red'
            alpha[i] = 1

        sizes = [10 for i in range(H.number_of_nodes())]
        sizes[node_index] = 15

        # set select value
        select.value = node_label

    else:
        bar.renderers[0].data_source.selected.indices = list()

        line_cols = ['#c6c6c6' for i in range(H.number_of_nodes())]
        alpha = [1 for i in range(H.number_of_nodes())]
        sizes = [10 for i in range(H.number_of_nodes())]

        select.value = '-'

    graph.node_renderer.data_source.data['line_colors'] = line_cols
    graph.node_renderer.data_source.data['alpha'] = alpha
    graph.node_renderer.data_source.data['sizes'] = sizes

graph.node_renderer.data_source.selected.on_change("indices", selected_node)


########################################### Airport selection ##########################################################
def select_airport(attrname, old, new):
    if select.value == '-':
        graph.node_renderer.data_source.selected.indices = list()
        graph.edge_renderer.data_source.selected.indices = list()
        bar.renderers[0].data_source.selected.indices = list()

    else:
        for key, label in labels.items():
            if select.value == label:
                graph.node_renderer.data_source.selected.indices = [key]

                edge_set = set()
                index = 0
                for edge in H.edges():
                    if edge[0] == key or edge[1] == key:
                        edge_set.add(index)
                    index += 1
                    if len(edge_set) == H.degree[key]:
                        break

                graph.edge_renderer.data_source.selected.indices = list(edge_set)
                break


select.on_change("value", select_airport)


########################################### Airport selection ##########################################################
def select_bar(attrname, old, new):
    if not bar.renderers[0].data_source.selected.indices:
        select.value = '-'
    else:
        select.value = labels_sort_arr[bar.renderers[0].data_source.selected.indices[0]]


bar.renderers[0].data_source.selected.on_change("indices", select_bar)

########################################### Arrange plots and controls #################################################
grid = gridplot([[None, select, None], [None, count_slider, None], [scroll_slider, bar, map]])
grid.children.pop(0)
curdoc().add_root(grid)
curdoc().title = "Visualization of airline travel in the USA"
show(grid)
