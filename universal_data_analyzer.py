"""
Universal Data Analyzer - Works with any type of data
Provides intelligent analysis and visualization suggestions
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Tuple, Any
import re


class DataIntelligence:
    """Intelligently analyze any dataset"""
    
    def __init__(self, df: pd.DataFrame):
        """Initialize with a dataframe"""
        self.df = df
        self.analyze_data_types()
    
    def analyze_data_types(self):
        """Analyze and categorize column types"""
        self.numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()
        self.datetime_cols = self.df.select_dtypes(include=['datetime64']).columns.tolist()
        self.bool_cols = self.df.select_dtypes(include=['bool']).columns.tolist()
        
        # Try to detect datetime columns from object type
        for col in self.categorical_cols:
            try:
                pd.to_datetime(self.df[col])
                self.datetime_cols.append(col)
                self.categorical_cols.remove(col)
            except:
                pass
    
    def get_data_summary(self) -> Dict:
        """Get comprehensive data summary"""
        summary = {
            "total_rows": len(self.df),
            "total_columns": len(self.df.columns),
            "numeric_columns": len(self.numeric_cols),
            "categorical_columns": len(self.categorical_cols),
            "datetime_columns": len(self.datetime_cols),
            "boolean_columns": len(self.bool_cols),
            "missing_values": self.df.isnull().sum().sum(),
            "missing_percentage": (self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns)) * 100),
            "numeric_stats": {},
            "categorical_stats": {}
        }
        
        # Numeric statistics
        for col in self.numeric_cols:
            summary["numeric_stats"][col] = {
                "mean": float(self.df[col].mean()),
                "median": float(self.df[col].median()),
                "std": float(self.df[col].std()),
                "min": float(self.df[col].min()),
                "max": float(self.df[col].max()),
            }
        
        # Categorical statistics
        for col in self.categorical_cols:
            summary["categorical_stats"][col] = {
                "unique_values": self.df[col].nunique(),
                "top_value": str(self.df[col].mode()[0]) if len(self.df[col].mode()) > 0 else "N/A",
                "value_counts": self.df[col].value_counts().head(5).to_dict()
            }
        
        return summary
    
    def get_column_insights(self, column: str) -> Dict:
        """Get detailed insights for a specific column"""
        if column not in self.df.columns:
            return {}
        
        insights = {
            "name": column,
            "type": str(self.df[column].dtype),
            "non_null_count": self.df[column].notna().sum(),
            "null_count": self.df[column].isna().sum()
        }
        
        if column in self.numeric_cols:
            insights.update({
                "mean": float(self.df[column].mean()),
                "median": float(self.df[column].median()),
                "std": float(self.df[column].std()),
                "min": float(self.df[column].min()),
                "max": float(self.df[column].max()),
                "q1": float(self.df[column].quantile(0.25)),
                "q3": float(self.df[column].quantile(0.75)),
                "skewness": float(self.df[column].skew()),
                "kurtosis": float(self.df[column].kurtosis())
            })
        
        elif column in self.categorical_cols:
            value_counts = self.df[column].value_counts()
            insights.update({
                "unique_values": len(value_counts),
                "top_5_values": value_counts.head(5).to_dict(),
                "diversity": len(value_counts) / len(self.df)  # Entropy proxy
            })
        
        return insights
    
    def suggest_visualizations(self) -> List[Dict]:
        """Suggest appropriate visualizations based on data"""
        suggestions = []
        
        # Numeric vs Numeric
        if len(self.numeric_cols) >= 2:
            suggestions.append({
                "type": "scatter",
                "title": f"Relationship: {self.numeric_cols[0]} vs {self.numeric_cols[1]}",
                "x": self.numeric_cols[0],
                "y": self.numeric_cols[1],
                "description": "Scatter plot to visualize correlation"
            })
            
            suggestions.append({
                "type": "line",
                "title": f"Trend: {self.numeric_cols[0]}",
                "x": list(range(len(self.df))),
                "y": self.numeric_cols[0],
                "description": "Line chart to show trends over index"
            })
        
        # Categorical vs Numeric
        if len(self.categorical_cols) >= 1 and len(self.numeric_cols) >= 1:
            suggestions.append({
                "type": "bar",
                "title": f"Distribution by {self.categorical_cols[0]}",
                "x": self.categorical_cols[0],
                "y": self.numeric_cols[0],
                "description": "Bar chart showing numeric distribution by category"
            })
        
        # Categorical only
        if len(self.categorical_cols) >= 1:
            suggestions.append({
                "type": "pie",
                "title": f"Distribution of {self.categorical_cols[0]}",
                "names": self.categorical_cols[0],
                "description": "Pie chart showing categorical distribution"
            })
        
        # Multiple numerics - box plot
        if len(self.numeric_cols) >= 2:
            suggestions.append({
                "type": "box",
                "title": "Statistical Distribution of Numeric Columns",
                "description": "Box plot to compare distributions"
            })
        
        # Histogram for numeric
        if len(self.numeric_cols) >= 1:
            suggestions.append({
                "type": "histogram",
                "title": f"Distribution of {self.numeric_cols[0]}",
                "x": self.numeric_cols[0],
                "description": "Histogram showing distribution of numeric values"
            })
        
        return suggestions
    
    def create_visualization(self, viz_type: str, x_col: str = None, y_col: str = None, 
                            category_col: str = None, title: str = None) -> Any:
        """Create a visualization based on type and columns"""
        
        title = title or f"{viz_type.upper()} Visualization"
        
        try:
            if viz_type == "scatter":
                return px.scatter(self.df, x=x_col, y=y_col, title=title, 
                                 labels={x_col: x_col, y_col: y_col})
            
            elif viz_type == "line":
                return px.line(self.df, x=x_col, y=y_col, title=title)
            
            elif viz_type == "bar":
                return px.bar(self.df, x=x_col, y=y_col, title=title)
            
            elif viz_type == "pie":
                value_counts = self.df[x_col].value_counts()
                return px.pie(values=value_counts.values, names=value_counts.index, 
                             title=title)
            
            elif viz_type == "histogram":
                return px.histogram(self.df, x=x_col, title=title, nbins=30)
            
            elif viz_type == "box":
                return px.box(self.df, y=self.numeric_cols, title=title)
            
            elif viz_type == "area":
                return px.area(self.df, x=x_col, y=y_col, title=title)
            
            elif viz_type == "violin":
                return px.violin(self.df, y=y_col, x=x_col, title=title)
            
            return None
        except Exception as e:
            return None
    
    def get_top_records(self, column: str, n: int = 5, ascending: bool = False) -> pd.DataFrame:
        """Get top N records sorted by column"""
        if column not in self.df.columns:
            return pd.DataFrame()
        
        return self.df.nlargest(n, column) if not ascending else self.df.nsmallest(n, column)
    
    def get_statistical_summary(self) -> str:
        """Get a text summary of statistics"""
        summary_text = f"""
        📊 DATASET OVERVIEW
        ──────────────────────
        Total Records: {len(self.df):,}
        Total Columns: {len(self.df.columns)}
        
        🔢 NUMERIC COLUMNS: {len(self.numeric_cols)}
        {', '.join(self.numeric_cols[:5])}{'...' if len(self.numeric_cols) > 5 else ''}
        
        🏷️ CATEGORICAL COLUMNS: {len(self.categorical_cols)}
        {', '.join(self.categorical_cols[:5])}{'...' if len(self.categorical_cols) > 5 else ''}
        
        📅 DATETIME COLUMNS: {len(self.datetime_cols)}
        {', '.join(self.datetime_cols[:5])}{'...' if len(self.datetime_cols) > 5 else ''}
        
        ⚠️ DATA QUALITY
        Missing Values: {self.df.isnull().sum().sum()} ({self.df.isnull().sum().sum() / (len(self.df) * len(self.df.columns)) * 100:.2f}%)
        Duplicate Rows: {self.df.duplicated().sum()}
        """
        return summary_text
    
    def filter_data(self, column: str, values: List = None, min_val: float = None, 
                   max_val: float = None) -> pd.DataFrame:
        """Filter data by column values or range"""
        filtered = self.df.copy()
        
        if values is not None:
            filtered = filtered[filtered[column].isin(values)]
        
        if min_val is not None and max_val is not None:
            filtered = filtered[(filtered[column] >= min_val) & (filtered[column] <= max_val)]
        
        return filtered
    
    def get_correlations(self, threshold: float = 0.5) -> Dict:
        """Get correlations between numeric columns"""
        if len(self.numeric_cols) < 2:
            return {}
        
        corr_matrix = self.df[self.numeric_cols].corr()
        strong_correlations = {}
        
        for i, col1 in enumerate(self.numeric_cols):
            for col2 in self.numeric_cols[i+1:]:
                corr_value = corr_matrix.loc[col1, col2]
                if abs(corr_value) >= threshold:
                    strong_correlations[f"{col1} <-> {col2}"] = float(corr_value)
        
        return strong_correlations
    
    def find_outliers(self, column: str, method: str = 'iqr') -> pd.DataFrame:
        """Find outliers in numeric columns"""
        if column not in self.numeric_cols:
            return pd.DataFrame()
        
        if method == 'iqr':
            Q1 = self.df[column].quantile(0.25)
            Q3 = self.df[column].quantile(0.75)
            IQR = Q3 - Q1
            outliers = self.df[(self.df[column] < Q1 - 1.5*IQR) | (self.df[column] > Q3 + 1.5*IQR)]
        
        elif method == 'zscore':
            z_scores = np.abs((self.df[column] - self.df[column].mean()) / self.df[column].std())
            outliers = self.df[z_scores > 3]
        
        else:
            outliers = pd.DataFrame()
        
        return outliers
    
    def group_analysis(self, group_col: str, agg_col: str = None, 
                      agg_func: str = 'count') -> pd.DataFrame:
        """Perform group-based analysis"""
        if group_col not in self.df.columns:
            return pd.DataFrame()
        
        if agg_col is None:
            agg_col = self.numeric_cols[0] if self.numeric_cols else group_col
        
        if agg_func == 'count':
            return self.df.groupby(group_col).size().reset_index(name='count')
        
        elif agg_col in self.numeric_cols:
            return self.df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
        
        return pd.DataFrame()
    
    def get_recommendations(self) -> List[str]:
        """Get analysis recommendations"""
        recommendations = []
        
        # Missing data recommendation
        if self.df.isnull().sum().sum() > 0:
            recommendations.append(f"⚠️ Dataset contains {self.df.isnull().sum().sum()} missing values. Consider data cleaning.")
        
        # Duplicate data recommendation
        if self.df.duplicated().sum() > 0:
            recommendations.append(f"🔄 Found {self.df.duplicated().sum()} duplicate rows. Review for data quality.")
        
        # Imbalanced data
        if len(self.categorical_cols) > 0:
            for col in self.categorical_cols[:2]:
                value_counts = self.df[col].value_counts()
                if len(value_counts) > 0:
                    ratio = value_counts.max() / value_counts.min()
                    if ratio > 10:
                        recommendations.append(f"⚖️ Column '{col}' shows imbalanced distribution (ratio: {ratio:.1f})")
        
        # Skewed numeric data
        for col in self.numeric_cols[:3]:
            skewness = self.df[col].skew()
            if abs(skewness) > 1:
                recommendations.append(f"📊 Column '{col}' has high skewness ({skewness:.2f}). Consider transformation.")
        
        # Correlation recommendations
        correlations = self.get_correlations(threshold=0.8)
        if correlations:
            recommendations.append(f"🔗 Found strong correlations: {list(correlations.keys())[:2]}")
        
        if not recommendations:
            recommendations.append("✅ Dataset appears clean and well-balanced!")
        
        return recommendations


class SmartChatContext:
    """Build intelligent context for chat interactions"""
    
    def __init__(self, df: pd.DataFrame, filename: str = "data.csv"):
        """Initialize with dataframe"""
        self.df = df
        self.filename = filename
        self.intelligence = DataIntelligence(df)
        self.summary = self.intelligence.get_data_summary()
    
    def build_chat_prompt(self) -> str:
        """Build comprehensive prompt for AI chatbot"""
        
        prompt = f"""
You are an expert data analyst AI chatbot. You have been given access to a dataset and should analyze it intelligently.

📊 DATASET INFORMATION:
- File: {self.filename}
- Rows: {self.summary['total_rows']:,}
- Columns: {self.summary['total_columns']}
- Numeric Columns: {self.summary['numeric_columns']} ({', '.join(self.intelligence.numeric_cols[:5])})
- Categorical Columns: {self.summary['categorical_columns']} ({', '.join(self.intelligence.categorical_cols[:5])})
- DateTime Columns: {self.summary['datetime_columns']}

📈 DATA QUALITY:
- Missing Values: {self.summary['missing_values']} ({self.summary['missing_percentage']:.2f}%)
- Data Types: {len(set(self.df.dtypes))} unique types

🎯 YOUR ROLE:
- Analyze the user's question about the data
- Provide insights and patterns
- Suggest visualizations when relevant
- Give actionable recommendations
- Explain complex patterns in simple terms
- Handle questions about any column in the data
- Suggest further analysis opportunities

💡 INSTRUCTIONS:
1. Understand the context of the question
2. Identify which columns are relevant
3. Provide specific insights with numbers
4. Suggest visualizations using this format when appropriate:
   {{
     "action": "visualize",
     "chart": "bar/line/scatter/pie/histogram",
     "title": "Chart Title",
     "x": "column_name",
     "y": "column_name"
   }}
5. For non-visualization questions, provide clear text analysis
6. Always include relevant statistics and patterns
7. Ask clarifying questions if the user's intent is unclear

⚠️ IMPORTANT:
- Work with ANY type of data, not just sales/customer data
- Be flexible in your analysis approach
- Provide both quantitative and qualitative insights
- Suggest next steps for deeper analysis
"""
        return prompt
    
    def get_contextual_suggestions(self, user_question: str) -> List[str]:
        """Get suggestions based on user's question"""
        suggestions = []
        
        question_lower = user_question.lower()
        
        # Detect analysis type
        if any(word in question_lower for word in ['top', 'best', 'highest', 'most']):
            if self.intelligence.numeric_cols:
                suggestions.append(f"Try: 'Show me the top 10 records by {self.intelligence.numeric_cols[0]}'")
        
        if any(word in question_lower for word in ['trend', 'time', 'over', 'change']):
            if self.intelligence.datetime_cols:
                suggestions.append(f"Try: 'Show trends over time using {self.intelligence.datetime_cols[0]}'")
        
        if any(word in question_lower for word in ['compare', 'difference', 'vs', 'versus']):
            if self.intelligence.categorical_cols:
                suggestions.append(f"Try: 'Compare values across {self.intelligence.categorical_cols[0]}'")
        
        if any(word in question_lower for word in ['distribution', 'spread', 'pattern']):
            if self.intelligence.numeric_cols:
                suggestions.append(f"Try: 'Show distribution of {self.intelligence.numeric_cols[0]}'")
        
        return suggestions
    
    def get_sample_questions(self) -> List[str]:
        """Get sample questions based on data"""
        questions = []
        
        # Based on numeric columns
        if self.intelligence.numeric_cols:
            col = self.intelligence.numeric_cols[0]
            questions.append(f"What is the average {col}?")
            questions.append(f"Show me the top 10 by {col}")
        
        # Based on categorical columns
        if self.intelligence.categorical_cols:
            col = self.intelligence.categorical_cols[0]
            questions.append(f"What are the unique values in {col}?")
            questions.append(f"How many records for each {col}?")
        
        # Generic questions
        questions.extend([
            "What patterns do you see in this data?",
            "Are there any outliers or anomalies?",
            "What correlations exist between columns?",
            "What are your recommendations for this data?",
            "Show me a summary of the data"
        ])
        
        return questions


def format_analysis_response(data: Any) -> str:
    """Format data analysis response"""
    if isinstance(data, pd.DataFrame):
        return data.to_string()
    elif isinstance(data, dict):
        return "\n".join([f"{k}: {v}" for k, v in data.items()])
    elif isinstance(data, list):
        return "\n".join([str(item) for item in data])
    else:
        return str(data)
