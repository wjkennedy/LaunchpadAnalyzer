import streamlit as st
from launchpadlib.launchpad import Launchpad
import pandas as pd
import plotly.express as px

# Cache directory for storing credentials
CACHE_DIR = "~/.launchpadlib/cache/"

# Add a header with the LinkedIn post link
st.markdown("""
# What does Critical Infrastructure look like? What do you think it looks like?

## Expanding on my post about [Canonical Launchpad](https://www.linkedin.com/posts/william-j-kennedy_launchpad-activity-7234522722301595648-VhSO?utm_source=share&utm_medium=member_desktop)

It’s where Ubuntu engineering happens, and it’s a Canonical invention…

Rather than use GitHub and Jira, as so many software products might, Canonical Engineers (and Users) also make the software to make “The Software” ([Learn more](https://lnkd.in/dW2qezNE)).

Ubuntu is so prevalent, Microsoft have recently stopped reporting on their own Server software sales because Ubuntu is such a proportionately larger piece of Azure's cloud compute offering (and sales).

Your favorite SaaS uses it — by default (!)

Your favorite websites depend on what Launchpad offers in terms of Developer Experience. Could it be better?
""")

# Application name for OAuth
APP_NAME = "Canonical_Launchpad_Analytics"

# Authenticate with Launchpad using OAuth2
def authenticate_with_launchpad():
    st.sidebar.write("Authenticating with Launchpad...")

    # Authenticate with Launchpad and get the Launchpad object
    launchpad = Launchpad.login_with(APP_NAME, "production", CACHE_DIR, version="devel")

    # Display authenticated user
    me = launchpad.me
    st.sidebar.success(f"Authenticated as: {me.display_name}")

    return launchpad

# Fetch available series (releases) for the project
def get_available_series(launchpad, project_name):
    st.write(f"Fetching available releases (series) for project: {project_name}...")

    project = launchpad.projects[project_name]
    
    # Fetch all the series/releases associated with this project
    releases = project.series

    release_names = []
    for release in releases:
        st.write(f"Series: {release.name} (Version: {release.version})")
        release_names.append(release.name)
    
    return release_names

# Fetch bugs for a selected release and return a DataFrame
def get_bugs_for_release(launchpad, project_name, release_name, bug_statuses):
    st.write(f"Fetching bugs for project: {project_name}, release: {release_name}...")

    # Fetch the project
    project = launchpad.projects[project_name]

    # Fetch the selected series by name
    series = None
    for s in project.series:
        if s.name == release_name:
            series = s
            break

    if not series:
        st.error(f"Release {release_name} not found for project {project_name}")
        return pd.DataFrame()

    # Query bugs linked to this series/release with filters
    bugs = series.searchTasks(status=bug_statuses)

    # Convert bug data into a list of dictionaries
    bug_data = []
    for bug in bugs:
        bug_data.append({
            "Bug ID": bug.bug.id,
            "Title": bug.bug.title,
            "Status": bug.status,
            "Date Created": bug.bug.date_created,
            "Date Last Updated": bug.bug.date_last_updated,
        })

    # Convert list of dictionaries into a DataFrame
    df_bugs = pd.DataFrame(bug_data)

    # Convert datetime columns to UTC and remove timezone information
    df_bugs["Date Created"] = pd.to_datetime(df_bugs["Date Created"], utc=True).dt.tz_localize(None)
    df_bugs["Date Last Updated"] = pd.to_datetime(df_bugs["Date Last Updated"], utc=True).dt.tz_localize(None)

    return df_bugs

# Perform OAuth2 authentication
launchpad = authenticate_with_launchpad()

# Sidebar filters
project_name = st.sidebar.text_input("Enter Launchpad Project Name", "ubuntu")
if launchpad and project_name:
    available_series = get_available_series(launchpad, project_name)
    release_name = st.sidebar.selectbox("Select Ubuntu Release", available_series)
    bug_statuses = st.sidebar.multiselect("Select Bug Status", ["New", "Confirmed", "In Progress", "Fix Committed", "Fix Released"], default=["New", "In Progress"])

    # Fetch and display project data if authenticated
    if release_name:
        df_bugs = get_bugs_for_release(launchpad, project_name, release_name, bug_statuses)
        st.write(f"Found {len(df_bugs)} bugs for release: {release_name}")
        
        # Show the DataFrame in Streamlit
        st.dataframe(df_bugs)
        
        # If there are bugs, create visualizations
        if not df_bugs.empty:
            # Create a Plotly bar chart for bug statuses
            fig = px.bar(df_bugs, x="Status", title="Bug Status Distribution", color="Status")
            st.plotly_chart(fig)
            
            # Create a Plotly timeline of bug creation
            fig2 = px.scatter(df_bugs, x="Date Created", y="Bug ID", color="Status", hover_data=["Title"], title="Bug Creation Timeline")
            st.plotly_chart(fig2)

