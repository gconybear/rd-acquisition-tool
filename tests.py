import streamlit as st
import pandas as pd
import geopandas as gpd
from geocoding import parse_address_string

#Import folium and related plugins
import folium
from folium import Marker
from folium.plugins import MarkerCluster
import json
from geomapping import TractMapper
import gmaps
# import download_file

# use this: https://jingwen-z.github.io/how-to-draw-a-variety-of-maps-with-folium-in-python/

st.set_page_config(layout='centered', page_icon='🔎')

def blank(): return st.text("")

@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

@st.cache(allow_output_mutation=True)
def get_data():
    # global data
    # data = gpd.read_file('data/test.geojson')
    #
    # global jdata
    # jdata = json.load(open('data/test.geojson', 'r'))

    global tm
    tm = TractMapper()

    return tm

TILES = {
    'cartodbdark_matter': 'cartodbdark_matter',
    'cartodbpositron': 'cartodbpositron',
    'OpenStreetMap': 'OpenStreetMap',
    'Stamen Toner': 'Stamen Toner',
    'Stamen Terrain': 'Stamen Terrain',
    # 'stadia': 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png'
}

from branca.colormap import linear, LinearColormap
from assets.colors import COLORS

nbh_count_colormap = linear.YlGnBu_09.scale(1, 5)
other_cm = LinearColormap(colors=[COLORS[x] for x in COLORS],
                        index=[1,2,3,4,5]
)

def display_map(tmapper=None, yes=False, lat=None, long=None, n=None, comps=False, comp_df=None):
    if yes:
        nearest = tmapper.get_n_nearest(lat, long, n=n)
        # fjl
        # jsondata = gpd.GeoDataFrame(nearest).to_json()
        gpddata = gpd.GeoDataFrame(nearest)
        m = folium.Map([lat, long], zoom_start=11) # tiles=TILES[tile]

        style_function = lambda x : {
            'fillColor': other_cm(x['properties']['cluster prediction']),
            'color': 'gray',
            'weight': 2.5,
            'fillOpacity': 0.35
        }

        highlight_function = lambda x: {'fillColor': '#000000',
                                'color':'#000000',
                                'fillOpacity': 0.4,
                                'weight': 0.5}

        folium.GeoJson(gpddata, style_function=style_function, highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(
            fields=['city', 'cluster prediction',  'cluster 1 probability',
                     'cluster 2 probability',
                     'cluster 3 probability',
                     'cluster 4 probability',
                     'cluster 5 probability', 'crimes per sq. mile',
                     'per capita income', 'pop. change', 'most similar RD stores',
                     'RD match index', 'similar store revenue', 'similar store noi',
                     'similar store bad debt'],
            localize=True
        )).add_to(m)

        for sty in TILES:
            folium.raster_layers.TileLayer(TILES[sty]).add_to(m)

        folium.LayerControl().add_to(m)

        folium.Marker(location=[lat, long], draggable=False,
        popup="""lat: {}, long: {}""".format(
                        round(lat, 3), round(long, 3)),
                      icon=folium.Icon(color='lightgray')).add_to(m)

        if comps:
            for i in range(0,len(comp_df)):
                html = f"""
                <h5>name</h5> {comp_df.iloc[i]['name']}<br>
                <h5>address</h5> {comp_df.iloc[i]['address']}<br>
                <h5>rating</h5> {comp_df.iloc[i]['rating']}<br>
                <h5>number of ratings</h5> {comp_df.iloc[i]['num_ratings']}<br>
                """

                iframe = folium.IFrame(html=html, width=400, height=200)
                popup = folium.Popup(iframe, max_width=1000)

                folium.Marker(
                  location=[comp_df.iloc[i]['lat_location'], comp_df.iloc[i]['long_location']],
                  popup=popup
                ).add_to(m)

    else:
        pass
        # m = folium.Map([28.775537, -81.311504], tiles='OpenStreetMap', zoom_start=11)
        #
        # # Add polygon boundary to folium map
        # folium.GeoJson(jdata, style_function = lambda x: {'color': 'blue','weight': 2.5,'fillOpacity': 0.3},
        # name='Orlando').add_to(m)


    # # Add marker for Location
    # folium.Marker(location=point,
    # popup="""
    #               <i>BC Concentration: </i> <br> <b>{}</b> ug/m3 <br> <hr>
    #               <i>NO<sub>2</sub> Concentration: </i><b><br>{}</b> ppb <br>
    #               """.format(
    #                 round(df.loc[spatial.KDTree(df[['Latitude', 'Longitude']]).query(point)[1]]['BC_Predicted_XGB'],2),
    #                 round(df.loc[spatial.KDTree(df[['Latitude', 'Longitude']]).query(point)[1]]['NO2_Predicted_XGB'],2)),
    #               icon=folium.Icon()).add_to(m)

    download_button = st.download_button(
                label='Download map',
                data=m._repr_html_(),
                file_name='analysis_map.html',
                mime='text/html'
            )

    return st.markdown(m._repr_html_(), unsafe_allow_html=True), blank(), download_button

def main():
    st.header("Red Dot Cluster Analysis Tool")
    st.text("")
    st.markdown('<p class="big-font"> Use this to visualize and analyze clusters at a neighborhood level </p>', unsafe_allow_html=True)
    st.write("[Link](https://app.powerbi.com/groups/b66220e0-ddcd-41a2-9dd8-5e489b4d3cd5/reports/a18b35ba-57d6-4dd6-bbad-85ed5146c9a8/ReportSectioned58b55d2641de7e8134) to the Power BI dashboard")
    st.text("")
    with st.form(key='form'):
        st.markdown('<p class="big-font"> <b> Enter an address, city, or town name below </b> </p>', unsafe_allow_html=True)
        address = st.text_input("Enter address or city", "Pine Bluff, Arkansas")
        N = st.slider("How many neighborhoods do you want to see?", 1, 100, 15, 5)
        show_competitors = st.checkbox("show self-storage supply", value=False, help='Use sparingly!')
        blank()
        submit_button = st.form_submit_button(label='Search')

    if submit_button:
        # Use the convert_address function to convert address to coordinates
        coordinates = parse_address_string(address)

        tmapper = get_data()

        #Call the display_map function by passing coordinates, dataframe and geoJSON file
        st.text("")
        # col0, col1, col2, col3, col4, col5 = st.columns(6)
        # with col0:
        #     st.write("")
        # col1.metric("Crime", "3.7", "1.2 %")
        # col2.metric("Education", "-2.1", "-8 %")
        # col3.metric("Life Change", "1.0", "0.6 %")
        # col4.metric("SEO", "10 %", "50 %")
        # with col5:
        #     st.write("")
        # st.text("")

        if 'lat' in coordinates:
            if show_competitors:
                dat = gmaps.get_competitor_meta(coordinates['lat'], coordinates['long'])
                cdf = dat['full'].copy()
                display_map(tmapper, True, coordinates['lat'], coordinates['long'], N, comps=True, comp_df=cdf)
            else:
                display_map(tmapper, True, coordinates['lat'], coordinates['long'], N)
        else:
            display_map()

        st.text("")
        st.markdown("Demographic Data")
        st.text("")
        df = tmapper.compare_demographics()
        st.dataframe(df)
        blank()
        if show_competitors:
            st.markdown("Competitor Data")
            display_comp_df = cdf[['name', 'address', 'rating', 'num_ratings', 'lat_location', 'long_location']]
            st.download_button(
                label='Download data',
                data=convert_df(display_comp_df),
                file_name=f"{str(address).replace(' ', '-')}_competitors.csv",
                mime='text/csv'
            )
            st.dataframe(display_comp_df)
        # st.markdown(download_file.get_table_download_link(df), unsafe_allow_html=True)
        # download_button_str = download_file.download_button(
        #     df,
        #     f'{address}_data.csv',
        #     'Download data',
        #     pickle_it=False
        # )
        #
        # st.markdown(download_button_str, unsafe_allow_html=True)

main()
