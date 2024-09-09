import streamlit as st
from launchpadlib.launchpad import Launchpad
import pandas as pd
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import stopwords

# Download NLTK stopwords
nltk.download('stopwords')

# Add a header with the LinkedIn post link
st.markdown("""
# What does Critical Infrastructure look like? What do you think it looks like?

### [Here is an example: Canonical Launchpad](https://www.linkedin.com/posts/william-j-kennedy_launchpad-activity-7234522722301595648-VhSO?utm_source=share&utm_medium=member_desktop)

It’s where Ubuntu engineering happens, and it’s a Canonical invention…

Rather than use GitHub and Jira, as so many software products might, Canonical Engineers (and Users) also make the software to make “The Software” ([Learn more](https://lnkd.in/dW2qezNE)).

Ubuntu is so prevalent, Microsoft have recently stopped reporting on their own Server software sales because Ubuntu is such a proportionately larger piece of Azure's cloud compute offering (and sales).

Your favorite SaaS uses it — by default (!)

Your favorite websites depend on what Launchpad offers in terms of Developer Experience. Could it be better?
""")

# Cache directory for storing credentials
CACHE_DIR = "~/.launchpadlib/cache/"

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
        # Safely handle the case where 'version' attribute may not be available
        version = getattr(release, 'version', 'N/A')  # Default to 'N/A' if version doesn't exist
        st.write(f"Series: {release.name} (Version: {version})")
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

    # Convert bug data into a list of dictionaries, using .get() to handle missing values
    bug_data = []
    for bug in bugs:
        bug_data.append({
            "Bug ID": bug.bug.id,
            "Title": bug.bug.title,
            "Description": getattr(bug.bug, 'description', ''),  # Add description for clustering
            "Status": bug.status,
            "Date Created": getattr(bug.bug, 'date_created', None),
            "Date Last Updated": getattr(bug.bug, 'date_last_updated', None),
        })

    # Convert list of dictionaries into a DataFrame
    df_bugs = pd.DataFrame(bug_data)

    # Convert datetime columns to UTC and remove timezone information, handle missing values
    if "Date Created" in df_bugs.columns:
        df_bugs["Date Created"] = pd.to_datetime(df_bugs["Date Created"], errors='coerce', utc=True).dt.tz_localize(None)
    if "Date Last Updated" in df_bugs.columns:
        df_bugs["Date Last Updated"] = pd.to_datetime(df_bugs["Date Last Updated"], errors='coerce', utc=True).dt.tz_localize(None)

    return df_bugs

# K-means clustering on bug titles and descriptions
def perform_clustering(df_bugs, n_clusters=5):
    st.subheader(f"K-means Clustering of {len(df_bugs)} Bugs")
    
    # Combine title and description for clustering
    combined_text = df_bugs['Title'] + ' ' + df_bugs['Description']
    
    # TF-IDF Vectorization
    vectorizer = TfidfVectorizer(stop_words=stopwords.words('english'), max_features=1000)
    X = vectorizer.fit_transform(combined_text)
    
    # K-means Clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    df_bugs['Cluster'] = kmeans.fit_predict(X)
    
    # Display cluster distribution
    st.write(f"Cluster distribution:")
    st.write(df_bugs['Cluster'].value_counts())
    
    # Visualize clusters
    fig = px.scatter(df_bugs, x="Date Created", y="Cluster", color="Cluster", hover_data=["Title"], title="K-means Bug Clustering")
    st.plotly_chart(fig)

# Multi-page navigation
page = st.sidebar.selectbox("Select Page", ["View Bugs", "Cluster Bugs"])

# Authenticate and proceed based on selected page
launchpad = authenticate_with_launchpad()

if launchpad:
    project_name = st.sidebar.text_input("Enter Launchpad Project Name", "ubuntu")
    if project_name:
        available_series = get_available_series(launchpad, project_name)
        release_name = st.sidebar.selectbox("Select Ubuntu Release", available_series)
        bug_statuses = st.sidebar.multiselect("Select Bug Status", ["New", "Confirmed", "In Progress", "Fix Committed", "Fix Released"], default=["New", "In Progress"])

        if release_name:
            df_bugs = get_bugs_for_release(launchpad, project_name, release_name, bug_statuses)
            st.write(f"Found {len(df_bugs)} bugs for release: {release_name}")

            # Multi-page functionality
            if page == "View Bugs":
                st.dataframe(df_bugs)

                if not df_bugs.empty:
                    # Create a Plotly bar chart for bug statuses
                    fig = px.bar(df_bugs, x="Status", title="Bug Status Distribution", color="Status")
                    st.plotly_chart(fig)

                    # Create a Plotly timeline of bug creation
                    fig2 = px.scatter(df_bugs, x="Date Created", y="Bug ID", color="Status", hover_data=["Title"], title="Bug Creation Timeline")
                    st.plotly_chart(fig2)

            elif page == "Cluster Bugs":
                if not df_bugs.empty:
                    num_clusters = st.sidebar.slider("Select Number of Clusters", min_value=2, max_value=10, value=5)
                    perform_clustering(df_bugs, n_clusters=num_clusters)

