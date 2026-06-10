from __future__ import annotations

import json
import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import difflib
import streamlit as st
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import custom modules
from ai_client import ask_llama, DEFAULT_MODEL, AIClientError
from data_qa import load_table, build_dataset_context

# Try to import universal analyzer
try:
    from universal_data_analyzer import DataIntelligence, SmartChatContext
except ImportError:
    st.warning("universal_data_analyzer module not found.")
    DataIntelligence = None
    SmartChatContext = None


def map_column_name(requested: str, df: pd.DataFrame):
    if not requested or not isinstance(requested, str):
        return None
    cols = list(df.columns)
    if requested in cols:
        return requested
    lower_map = {c.lower(): c for c in cols}
    if requested.lower() in lower_map:
        return lower_map[requested.lower()]
    matches = difflib.get_close_matches(requested, cols, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    stripped = {''.join(ch for ch in c.lower() if ch.isalnum()): c for c in cols}
    key = ''.join(ch for ch in requested.lower() if ch.isalnum())
    if key in stripped:
        return stripped[key]
    # fallback to keyword matching for common names
    for col in cols:
        if col.lower() in requested.lower() or requested.lower() in col.lower():
            return col
    return None


def build_chart_from_question(question: str, df: pd.DataFrame):
    if not question or df is None:
        return None
    text = question.lower()

    # Respect the chart type the user explicitly asked for.
    # Words like "distribution" describe the analysis, not necessarily a pie chart.
    if any(term in text for term in ['stacked column', 'stacked bar', 'stacked']):
        chart_type = 'stacked'
    elif any(term in text for term in ['bar chart', 'bar graph', 'column chart', 'using bar', 'using column']):
        chart_type = 'bar'
    elif any(term in text for term in ['pie chart', 'donut chart', 'doughnut chart', 'using pie']):
        chart_type = 'pie'
    elif 'histogram' in text:
        chart_type = 'histogram'
    elif 'scatter' in text:
        chart_type = 'scatter'
    elif 'line' in text or 'trend' in text:
        chart_type = 'line'
    elif 'distribution' in text or 'proportion' in text or 'share of' in text:
        chart_type = 'pie'
    elif ' vs ' in text or ' vs.' in text or 'by ' in text:
        chart_type = 'bar'
    else:
        return None

    x_col = None
    y_col = None
    for col in df.columns:
        lower_col = col.lower()
        if lower_col in text and (x_col is None or lower_col in ['category', 'type', 'region', 'status']):
            x_col = col
        if lower_col in text and (y_col is None and pd.api.types.is_numeric_dtype(df[col])):
            y_col = col

    if ' vs ' in text or ' vs.' in text:
        parts = text.split(' vs ')
        if len(parts) == 2:
            left = map_column_name(parts[0].strip(), df)
            right = map_column_name(parts[1].strip(), df)
            if left:
                x_col = left
            if right:
                y_col = right

    if chart_type == 'pie':
        if x_col:
            title = 'Pie chart of ' + x_col
            if y_col and pd.api.types.is_numeric_dtype(df[y_col]):
                agg = df.groupby(x_col)[y_col].sum().reset_index()
                return px.pie(agg, names=x_col, values=y_col, title=title)
            return px.pie(df, names=x_col, title=title)
    elif chart_type == 'bar':
        if x_col and y_col:
            title = 'Bar chart of ' + y_col + ' by ' + x_col
            agg = df.groupby(x_col, dropna=False)[y_col].sum().reset_index()
            return px.bar(agg, x=x_col, y=y_col, title=title)
        if x_col:
            vc = df[x_col].value_counts().reset_index()
            vc.columns = [x_col, 'count']
            return px.bar(vc, x=x_col, y='count', title=f'Count by {x_col}')
    elif chart_type == 'stacked':
        categorical_cols = [
            col for col in df.columns
            if not pd.api.types.is_numeric_dtype(df[col])
        ]
        if len(categorical_cols) >= 2:
            x_col = x_col or categorical_cols[0]
            color_col = next((col for col in categorical_cols if col != x_col), categorical_cols[0])
            if y_col and pd.api.types.is_numeric_dtype(df[y_col]):
                agg = df.groupby([x_col, color_col], dropna=False)[y_col].sum().reset_index()
                return px.bar(agg, x=x_col, y=y_col, color=color_col, title=f'{y_col} by {x_col} and {color_col}')
            agg = df.groupby([x_col, color_col], dropna=False).size().reset_index(name='count')
            return px.bar(agg, x=x_col, y='count', color=color_col, title=f'Count by {x_col} and {color_col}')
    elif chart_type == 'line' and x_col and y_col:
        return px.line(df, x=x_col, y=y_col, title=f'{y_col} over {x_col}')
    elif chart_type == 'scatter' and x_col and y_col:
        return px.scatter(df, x=x_col, y=y_col, title=f'{y_col} vs {x_col}')
    elif chart_type == 'histogram' and x_col:
        return px.histogram(df, x=x_col, title=f'Distribution of {x_col}')
    return None


def is_visualization_question(question: str) -> bool:
    text = question.lower()
    keywords = [
        'visualize', 'visualization', 'chart', 'graph', 'plot',
        'pie', 'bar', 'histogram', 'stacked', 'column chart',
        'distribution', 'vs'
    ]
    return any(keyword in text for keyword in keywords)


def render_visualization_response(question: str, df: pd.DataFrame) -> bool:
    fig = build_chart_from_question(question, df)
    if fig is None:
        st.warning("I could not identify the columns for this visualization. Try: content type vs shares using bar chart")
        return False

    viz_tab, data_tab = st.tabs(["Visualization", "Actual Data"])
    with viz_tab:
        st.plotly_chart(fig, use_container_width=True)
    with data_tab:
        st.dataframe(df, use_container_width=True)
    return True

# Page configuration
st.set_page_config(
    page_title="AI Data Analyst - Universal Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤖 AI Data Analyst - Universal Data Explorer")
st.markdown("### Intelligent Analysis for ANY Dataset | AI-Powered Insights")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    model = st.text_input(
        "Model",
        value=DEFAULT_MODEL,
        help="AI Model to use for analysis"
    )
    
    api_key = st.text_input(
        "NVIDIA API Key",
        value=os.getenv("NVIDIA_API_KEY", ""),
        type="password",
        help="Your NVIDIA API Key for LLM access"
    )
    
    st.divider()
    st.header("📁 Data Source")

    # Simplified: only allow file upload (no sample/example data)
    data_source = st.radio(
        "Choose how to load data:",
        ["📤 Upload File"],
        help="Select data source"
    )
    st.markdown("**Upload CSV or Excel file to analyze**")

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = None

if "context" not in st.session_state:
    st.session_state.context = None

if "data_intelligence" not in st.session_state:
    st.session_state.data_intelligence = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

# Load data based on selection
if data_source == "📤 Upload File":
    uploaded_file = st.file_uploader(
        "Upload your data (CSV, Excel, etc.)",
        type=["csv", "xlsx", "xls"],
        help="Choose a file to analyze"
    )
    
    if uploaded_file:
        try:
            df = load_table(uploaded_file, uploaded_file.name)
            st.session_state.df = df
            st.session_state.context = build_dataset_context(df, uploaded_file.name)
            if DataIntelligence:
                st.session_state.data_intelligence = DataIntelligence(df)
            st.success(f"✅ Loaded: {uploaded_file.name} ({len(df)} rows, {len(df.columns)} columns)")
        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")

elif data_source == "💾 Sample Data":
    # Try to load sample data
    sample_files = ["preprocessed_sales_data.csv", "sales_data_sample.csv"]
    
    for sample_file in sample_files:
        file_path = Path(sample_file)
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                st.session_state.df = df
                st.session_state.context = build_dataset_context(df, sample_file)
                if DataIntelligence:
                    st.session_state.data_intelligence = DataIntelligence(df)
                st.success(f"✅ Loaded: {sample_file}")
                break
            except Exception as e:
                st.warning(f"Could not load {sample_file}: {str(e)}")

else:  # Example Dataset
    # Create sample dataset
    np.random.seed(42)
    sample_data = {
        'Date': pd.date_range('2024-01-01', periods=100),
        'Product': np.random.choice(['Laptop', 'Phone', 'Tablet', 'Monitor'], 100),
        'Sales': np.random.randint(100, 5000, 100),
        'Quantity': np.random.randint(1, 50, 100),
        'Region': np.random.choice(['North', 'South', 'East', 'West'], 100),
        'Category': np.random.choice(['Electronics', 'Accessories'], 100),
    }
    df = pd.DataFrame(sample_data)
    st.session_state.df = df
    st.session_state.context = build_dataset_context(df, "example_data.csv")
    if DataIntelligence:
        st.session_state.data_intelligence = DataIntelligence(df)
    st.success("✅ Example dataset loaded")

df = st.session_state.df
context = st.session_state.context
data_intelligence = st.session_state.data_intelligence

# Display data overview
if df is not None:
    st.divider()
    
    # Quick statistics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📈 Rows", f"{len(df):,}")
    col2.metric("📋 Columns", len(df.columns))
    col3.metric("💾 Size", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
    col4.metric("❌ Missing", df.isnull().sum().sum())
    col5.metric("🤖 Model", model.split("/")[-1] if "/" in model else model)
    
    # Data preview
    with st.expander("📊 Data Preview", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("First 5 Rows")
            st.dataframe(df.head(5), use_container_width=True)
        with col2:
            st.subheader("Data Info")
            if data_intelligence:
                info_text = data_intelligence.get_statistical_summary()
                st.markdown(info_text)
            else:
                st.write(df.info())
    
    # Data analysis tabs
    if data_intelligence:
        st.divider()
        st.header("📊 Data Intelligence")
        
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📈 Overview", "🔍 Columns", "📉 Statistics",  "💡 Insights"]
        )
        
        with tab1:
            st.subheader("Dataset Overview")
            summary = data_intelligence.get_data_summary()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Numeric Columns", summary['numeric_columns'])
            col2.metric("Categorical Columns", summary['categorical_columns'])
            col3.metric("DateTime Columns", summary['datetime_columns'])
            
            st.subheader("Column Details")
            col_display = pd.DataFrame({
                'Column': df.columns,
                'Type': [str(dtype) for dtype in df.dtypes],
                'Non-Null': df.notna().sum().values,
                'Unique': [df[col].nunique() for col in df.columns]
            })
            st.dataframe(col_display, use_container_width=True)
        
        with tab2:
            st.subheader("Detailed Column Analysis")
            
            selected_col = st.selectbox(
                "Select a column to analyze:",
                df.columns,
                key="col_select"
            )
            
            if selected_col:
                insights = data_intelligence.get_column_insights(selected_col)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Column:** {insights['name']}")
                    st.markdown(f"**Type:** {insights['type']}")
                    st.markdown(f"**Non-Null Count:** {insights['non_null_count']}")
                    st.markdown(f"**Null Count:** {insights['null_count']}")
                
                with col2:
                    if selected_col in data_intelligence.numeric_cols:
                        st.markdown(f"**Mean:** {insights['mean']:.2f}")
                        st.markdown(f"**Median:** {insights['median']:.2f}")
                        st.markdown(f"**Std Dev:** {insights['std']:.2f}")
                        st.markdown(f"**Min:** {insights['min']:.2f}")
                        st.markdown(f"**Max:** {insights['max']:.2f}")
                    elif selected_col in data_intelligence.categorical_cols:
                        st.markdown(f"**Unique Values:** {insights.get('unique_values', 'N/A')}")
                        st.markdown(f"**Top Value:** {insights.get('top_value', 'N/A')}")
                        st.markdown("**Value Counts:**")
                        top5 = insights.get('top_5_values') or {}
                        if top5:
                            for val, count in list(top5.items())[:5]:
                                st.markdown(f"- {val}: {count}")
                        else:
                            st.markdown("- No values available")
        
        with tab3:
            st.subheader("Statistical Analysis")
            
            if data_intelligence.numeric_cols:
                st.markdown("**Numeric Column Statistics**")
                numeric_stats = df[data_intelligence.numeric_cols].describe().T
                st.dataframe(numeric_stats, use_container_width=True)
       
        
        with tab4:
            st.subheader("📋 AI Recommendations")
            
            recommendations = data_intelligence.get_recommendations()
            for rec in recommendations:
                st.info(rec)
            
            # Correlations
            if len(data_intelligence.numeric_cols) >= 2:
                st.subheader("🔗 Strong Correlations")
                correlations = data_intelligence.get_correlations(threshold=0.5)
                if correlations:
                    for pair, corr_value in correlations.items():
                        st.markdown(f"- {pair}: **{corr_value:.3f}**")
                else:
                    st.info("No strong correlations found (threshold: 0.5)")


# AI Chatbot section
st.divider()
st.header("🤖 AI Chatbot - Ask Questions About Your Data")

if df is not None and context:
    
    # Create smart context
    smart_context = None
    if SmartChatContext and data_intelligence:
        smart_context = SmartChatContext(df, context.filename)
    
    # Chat interface
    col1, col2 = st.columns([4, 1])
    
    with col2:
        if st.button("💬 Sample Questions", use_container_width=True):
            st.info("Try asking:")
            if smart_context:
                for q in smart_context.get_sample_questions()[:3]:
                    st.markdown(f"- {q}")
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                if isinstance(message["content"], str):
                    st.markdown(message["content"])
                elif (
                    isinstance(message["content"], dict)
                    and message["content"].get("type") == "visualization"
                    and df is not None
                ):
                    render_visualization_response(message["content"].get("question", ""), df)
                else:
                    st.json(message["content"])
    
    # Chat input
    question = st.chat_input(
        "Ask about your data",
        key="chat_input"
    )
    
    if question:
        # Add user message
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })
        
        with st.chat_message("user"):
            st.markdown(question)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing data and generating insights..."):
                try:
                    if is_visualization_question(question):
                        shown = render_visualization_response(question, df)
                        response_content = {
                            "type": "visualization",
                            "question": question,
                            "rendered": shown,
                        }
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response_content
                        })
                        st.stop()

                    # Build intelligent context
                    if smart_context and SmartChatContext:
                        chat_prompt = smart_context.build_chat_prompt()
                        context_text = chat_prompt
                    else:
                        context_text = f"""
                        Dataset: {context.filename}
                        Rows: {len(df)}, Columns: {len(df.columns)}
                        Column names: {', '.join(context.column_names)}
                        """
                    
                    # Get AI response
                    answer = ask_llama(
                        question,
                        context_text,
                        context.column_names,
                        api_key=api_key,
                        model=model,
                    )
                    
                    # Try to parse and handle different response types
                    response_content = answer
                    
                    try:
                        # Try to parse JSON from the answer text, even if the AI includes extra text.
                        chart_data = None
                        try:
                            chart_data = json.loads(answer)
                        except json.JSONDecodeError:
                            # Find the first JSON object inside text by matching braces.
                            stack = 0
                            start = None
                            for index, ch in enumerate(answer):
                                if ch == '{':
                                    if stack == 0:
                                        start = index
                                    stack += 1
                                elif ch == '}':
                                    stack -= 1
                                    if stack == 0 and start is not None:
                                        snippet = answer[start:index + 1]
                                        try:
                                            chart_data = json.loads(snippet)
                                            break
                                        except json.JSONDecodeError:
                                            start = None
                                            continue

                        if chart_data is None:
                            raise json.JSONDecodeError("No valid JSON found", answer, 0)

                        # helper to fuzzy-map requested column names to df columns
                        def map_column(requested):
                            if not requested:
                                return None
                            cols = list(df.columns)
                            if requested in cols:
                                return requested
                            lower_map = {c.lower(): c for c in cols}
                            if requested.lower() in lower_map:
                                return lower_map[requested.lower()]
                            matches = difflib.get_close_matches(requested, cols, n=1, cutoff=0.6)
                            if matches:
                                return matches[0]
                            stripped = {''.join(ch for ch in c.lower() if ch.isalnum()): c for c in cols}
                            key = ''.join(ch for ch in requested.lower() if ch.isalnum())
                            return stripped.get(key)

                        def build_and_show(chart_dict):
                            chart_type = chart_dict.get('chart') or chart_dict.get('type') or 'bar'
                            title = chart_dict.get('title', 'Visualization')
                            x_req = chart_dict.get('x') or chart_dict.get('names') or chart_dict.get('column')
                            y_req = chart_dict.get('y') or chart_dict.get('value')

                            x_col = map_column(x_req) if x_req else None
                            y_col = map_column(y_req) if y_req else None

                            fig = None
                            try:
                                if chart_type == 'pie':
                                    if x_col and y_col:
                                        agg = df.groupby(x_col)[y_col].sum().reset_index()
                                        fig = px.pie(agg, names=x_col, values=y_col, title=title)
                                    elif x_col:
                                        fig = px.pie(df, names=x_col, title=title)
                                    elif y_col:
                                        fig = px.pie(df, names=y_col, title=title)
                                elif chart_type == 'bar':
                                    if x_col and y_col:
                                        fig = px.bar(df, x=x_col, y=y_col, title=title)
                                    elif x_col:
                                        vc = df[x_col].value_counts().reset_index()
                                        vc.columns = [x_col, 'count']
                                        fig = px.bar(vc, x=x_col, y='count', title=title)
                                elif chart_type == 'line':
                                    if x_col and y_col:
                                        fig = px.line(df, x=x_col, y=y_col, title=title)
                                elif chart_type == 'scatter':
                                    if x_col and y_col:
                                        fig = px.scatter(df, x=x_col, y=y_col, title=title)
                                elif chart_type == 'histogram':
                                    if x_col:
                                        fig = px.histogram(df, x=x_col, title=title)
                                else:
                                    if x_col:
                                        vc = df[x_col].value_counts().reset_index()
                                        vc.columns = [x_col, 'count']
                                        fig = px.bar(vc, x=x_col, y='count', title=title)
                            except Exception:
                                fig = None

                            if fig:
                                st.plotly_chart(fig, use_container_width=True)
                                st.markdown('*Visualization generated based on AI analysis*')
                                return True
                            return False

                        # Support either a single dict or list of actions
                        shown_any = False
                        if isinstance(chart_data, dict) and (chart_data.get('action') == 'visualize' or 'chart' in chart_data):
                            shown_any = build_and_show(chart_data)
                        elif isinstance(chart_data, list):
                            for item in chart_data:
                                if isinstance(item, dict) and (item.get('action') == 'visualize' or 'chart' in item):
                                    if build_and_show(item):
                                        shown_any = True

                        if not shown_any:
                            fallback_fig = build_chart_from_question(question, df)
                            if fallback_fig is not None:
                                st.plotly_chart(fallback_fig, use_container_width=True)
                                st.markdown('*Visualization generated from question intent*')
                            else:
                                st.markdown('```json\n' + json.dumps(chart_data, indent=2) + '\n```')

                    except json.JSONDecodeError:
                        fallback_fig = build_chart_from_question(question, df)
                        if fallback_fig is not None:
                            st.plotly_chart(fallback_fig, use_container_width=True)
                            st.markdown('*Visualization generated from question intent*')
                        else:
                            # Plain text response
                            st.markdown(answer)
                    
                    # Store response
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": response_content
                    })
                    
                except AIClientError as e:
                    error_msg = f"🔴 AI Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                
                except Exception as e:
                    error_msg = f"🔴 Unexpected error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    
                    # Fallback: provide basic analysis
                    st.info("💡 Trying basic analysis...")
                    try:
                        if "top" in question.lower() and data_intelligence:
                            if data_intelligence.numeric_cols:
                                col = data_intelligence.numeric_cols[0]
                                top_records = df.nlargest(5, col)[col]
                                st.write(f"Top 5 by {col}:")
                                st.bar_chart(top_records)
                    except:
                        pass

else:
    if df is None:
        st.info("📂 **Please load data first** - Use the sidebar to upload a file or select sample data")
    else:
        st.info("🔑 **API Configuration Required** - Enter your NVIDIA API Key in the sidebar to use the AI chatbot")
