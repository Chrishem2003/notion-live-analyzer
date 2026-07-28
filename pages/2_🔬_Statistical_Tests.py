# ═══════════════════════════════════════════════════════════════════════════════
# TEST: ONE-WAY ANOVA (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "One-Way ANOVA":
    if cat_cols and numeric_cols:
        group_col = st.selectbox("Factor (groups)", options=cat_cols)
        value_col = st.selectbox("Dependent variable", options=numeric_cols)
        
        norm = check_normality(active_df[value_col])
        homog = check_homogeneity(active_df, group_col, value_col)
        st.markdown("**Pre-Test Assumptions**")
        c1, c2 = st.columns(2)
        with c1: assumption_badge(norm["is_normal"], f"Normality: {norm['note']}")
        with c2: assumption_badge(homog["equal_var"], f"Homogeneity: {homog['note']}")
        
        if not norm["is_normal"]:
            st.warning("⚠️ Data appears non-normal. Consider using **Kruskal-Wallis H** instead.")
            if st.button("🔄 Switch to Kruskal-Wallis H", type="secondary"):
                st.session_state.selected_test_override = "Non-Parametric Tests → Kruskal-Wallis H"
                st.rerun()
        
        if st.button("▶️ Run One-Way ANOVA", type="primary"):
            result = engine.anova_one_way(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                groups = active_df.groupby(group_col)[value_col].apply(lambda x: x.dropna().count())
                result["df_between"] = len(groups) - 1
                result["df_within"] = groups.sum() - len(groups)
                
                assumptions = {**norm, "equal_var": homog["equal_var"], "series": active_df[value_col], "col_name": value_col}
                params = {"group_col": group_col, "value_col": value_col, "series": active_df[value_col]}
                render_result_panel(result, test_name, params, assumptions)
                
                fig = plot_boxplot_with_errorbars(active_df, group_col, value_col)
                st.plotly_chart(fig, use_container_width=True)
                
                if "post_hoc" in result and result["post_hoc"] is not None and not result["post_hoc"].empty:
                    st.subheader("📊 Post-Hoc Tukey HSD")
                    st.dataframe(result["post_hoc"], use_container_width=True, hide_index=True)
                    
                    ph = result["post_hoc"]
                    if "meandiff" in ph.columns and "lower" in ph.columns and "upper" in ph.columns:
                        labels = [f"{ph.iloc[i, 0]} vs {ph.iloc[i, 1]}" for i in range(len(ph))]
                        sizes = ph["meandiff"].tolist()
                        cis = [[ph["lower"].iloc[i], ph["upper"].iloc[i]] for i in range(len(ph))]
                        fig_ph = plot_forest_effect(sizes, labels, cis, "Post-Hoc Mean Differences (95% CI)")
                        st.plotly_chart(fig_ph, use_container_width=True)
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: TWO-WAY ANOVA (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Two-Way ANOVA":
    if len(cat_cols) >= 2 and numeric_cols:
        f1 = st.selectbox("Factor 1", options=cat_cols)
        f2 = st.selectbox("Factor 2", options=[c for c in cat_cols if c != f1])
        dep = st.selectbox("Dependent variable", options=numeric_cols)
        show_interaction = st.toggle("Show interaction plot", value=True)
        
        if st.button("▶️ Run Two-Way ANOVA", type="primary"):
            result = engine.anova_two_way(active_df, f1, f2, dep)
            if result is not None and not result.empty and "error" not in result.columns:
                st.dataframe(result, use_container_width=True, hide_index=True)
                
                sig_rows = result[result.get("PR(>F)", pd.Series([1]*len(result))) < 0.05] if "PR(>F)" in result.columns else pd.DataFrame()
                apa = f"A two-way ANOVA was conducted with {f1} and {f2} as independent variables and {dep} as the dependent variable."
                if not sig_rows.empty:
                    apa += f" Significant effects were found for: {', '.join(sig_rows.index.tolist())}."
                else:
                    apa += " No significant main effects or interactions were found."
                st.subheader("📄 APA-Style Report")
                st.code(apa, language="markdown")
                copy_to_clipboard_button(apa, "📋 Copy APA Report")
                
                if show_interaction:
                    st.plotly_chart(plot_interaction_2way(active_df, f1, f2, dep), use_container_width=True)
                
                log_analysis("Two-Way ANOVA", {"f1": f1, "f2": f2, "dep": dep}, result.to_dict())
            else:
                st.error("Two-Way ANOVA failed. Check data requirements.")
    else:
        st.warning("Need at least 2 categorical and 1 numeric variable.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: REPEATED MEASURES ANOVA (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Repeated Measures ANOVA":
    if len(numeric_cols) >= 2:
        st.info("Select 2+ measurements of the same subjects across conditions/time points.")
        measures = st.multiselect("Select repeated measures", options=numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
        
        if len(measures) >= 2:
            if st.button("▶️ Run Repeated Measures ANOVA", type="primary"):
                try:
                    from statsmodels.stats.anova import AnovaRM
                    df_melt = active_df[measures].reset_index().melt(id_vars=["index"], var_name="Condition", value_name="Score")
                    df_melt.columns = ["Subject", "Condition", "Score"]
                    aovrm = AnovaRM(df_melt, depvar="Score", subject="Subject", within=["Condition"])
                    res = aovrm.fit()
                    
                    st.subheader("📊 Results")
                    st.dataframe(res.anova_table, use_container_width=True)
                    st.info("💡 For full sphericity testing, export to Python/R. Greenhouse-Geisser correction applied if needed.")
                    
                    fig = px.box(df_melt, x="Condition", y="Score", points="all", color="Condition", template="plotly_white")
                    fig.update_layout(title="Repeated Measures by Condition", height=450)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    log_analysis("Repeated Measures ANOVA", {"measures": measures}, res.anova_table.to_dict())
                except Exception as e:
                    st.error(f"Repeated Measures ANOVA failed: {e}")
        else:
            st.warning("Select at least 2 repeated measures.")
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CHI-SQUARE TEST (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Chi-Square Test":
    if len(cat_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=cat_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in cat_cols if c != col1_c])
        show_expected = st.toggle("Show expected frequencies", value=False)
        
        if st.button("▶️ Run Chi-Square Test", type="primary"):
            result = engine.chi_square_test(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                params = {"col1": col1_c, "col2": col2_c}
                render_result_panel(result, test_name, params)
                
                st.subheader("Contingency Table")
                st.dataframe(result.get("contingency_table", pd.DataFrame()), use_container_width=True)
                
                if show_expected and "contingency_table" in result:
                    ct = result["contingency_table"]
                    chi2, _, _, expected = stats.chi2_contingency(ct)
                    expected_df = pd.DataFrame(expected, index=ct.index, columns=ct.columns)
                    st.subheader("Expected Frequencies")
                    st.dataframe(expected_df.round(2), use_container_width=True)
                
                ct = result.get("contingency_table", pd.DataFrame())
                if not ct.empty:
                    fig = px.imshow(ct.values, x=list(ct.columns), y=list(ct.index), 
                                    text_auto=True, color_continuous_scale="Blues", template="plotly_white")
                    fig.update_layout(title="Contingency Table Heatmap", height=400)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need at least 2 categorical variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FISHER'S EXACT TEST (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Fisher's Exact Test":
    if len(cat_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=cat_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in cat_cols if c != col1_c])
        
        if st.button("▶️ Run Fisher's Exact Test", type="primary"):
            ct = pd.crosstab(active_df[col1_c], active_df[col2_c])
            if ct.shape == (2, 2):
                oddsratio, p_value = stats.fisher_exact(ct)
                st.metric("Odds Ratio", f"{oddsratio:.4f}")
                st.metric("P-Value", f"{p_value:.6f}")
                st.metric("Significant", "✅ Yes" if p_value < 0.05 else "❌ No")
                
                apa = f"Fisher's exact test indicated a {'significant' if p_value < 0.05 else 'non-significant'} association, p = {p_value:.4f}, OR = {oddsratio:.2f}."
                st.subheader("📄 APA-Style Report")
                st.code(apa, language="markdown")
                copy_to_clipboard_button(apa, "📋 Copy APA Report")
                
                st.dataframe(ct, use_container_width=True)
                log_analysis("Fisher's Exact Test", {"col1": col1_c, "col2": col2_c}, {"oddsratio": oddsratio, "p": p_value})
            else:
                st.error("Fisher's Exact Test requires a 2×2 contingency table. Use Chi-Square for larger tables.")
    else:
        st.warning("Need at least 2 categorical variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MCNEMAR'S TEST (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "McNemar's Test":
    if len(binary_cats) >= 2 or (len(bool_cols) >= 2):
        available = binary_cats + bool_cols
        before = st.selectbox("Before / Condition 1", options=available)
        after = st.selectbox("After / Condition 2", options=[c for c in available if c != before])
        
        if st.button("▶️ Run McNemar's Test", type="primary"):
            ct = pd.crosstab(active_df[before], active_df[after])
            if ct.shape == (2, 2):
                result = stats.mcnemar(ct, exact=True)
                st.metric("Statistic", f"{result.statistic:.4f}")
                st.metric("P-Value", f"{result.pvalue:.6f}")
                st.metric("Significant", "✅ Yes" if result.pvalue < 0.05 else "❌ No")
                
                apa = f"McNemar's test indicated a {'significant' if result.pvalue < 0.05 else 'non-significant'} change in proportions, p = {result.pvalue:.4f}."
                st.subheader("📄 APA-Style Report")
                st.code(apa, language="markdown")
                copy_to_clipboard_button(apa, "📋 Copy APA Report")
                
                st.dataframe(ct, use_container_width=True)
                log_analysis("McNemar's Test", {"before": before, "after": after}, {"statistic": result.statistic, "p": result.pvalue})
            else:
                st.error("McNemar's test requires binary (2×2) paired data.")
    else:
        st.warning("Need at least 2 binary categorical variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: PEARSON CORRELATION (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Pearson Correlation":
    if len(numeric_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=numeric_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in numeric_cols if c != col1_c])
        
        norm1 = check_normality(active_df[col1_c])
        norm2 = check_normality(active_df[col2_c])
        st.markdown("**Pre-Test Assumptions**")
        c1, c2 = st.columns(2)
        with c1: assumption_badge(norm1["is_normal"], f"{col1_c} normality")
        with c2: assumption_badge(norm2["is_normal"], f"{col2_c} normality")
        
        if not (norm1["is_normal"] and norm2["is_normal"]):
            st.warning("⚠️ One or both variables are non-normal. Consider using **Spearman Correlation** instead.")
            if st.button("🔄 Switch to Spearman Correlation", type="secondary"):
                st.session_state.selected_test_override = "Correlation → Spearman Correlation"
                st.rerun()
        
        if st.button("▶️ Run Pearson Correlation", type="primary"):
            result = engine.pearson_correlation(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                params = {"col1": col1_c, "col2": col2_c}
                render_result_panel(result, test_name, params)
                
                fig = px.scatter(active_df, x=col1_c, y=col2_c, trendline="ols", template="plotly_white",
                                title=f"Scatter Plot: {col1_c} vs {col2_c}")
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: SPEARMAN CORRELATION (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Spearman Correlation":
    if len(numeric_cols) >= 2:
        col1_c = st.selectbox("Variable 1", options=numeric_cols)
        col2_c = st.selectbox("Variable 2", options=[c for c in numeric_cols if c != col1_c])
        
        if st.button("▶️ Run Spearman Correlation", type="primary"):
            result = engine.spearman_correlation(active_df, col1_c, col2_c)
            if "error" in result:
                st.error(result["error"])
            else:
                params = {"col1": col1_c, "col2": col2_c}
                render_result_panel(result, test_name, params)
                
                fig = px.scatter(active_df, x=col1_c, y=col2_c, template="plotly_white",
                                title=f"Scatter Plot: {col1_c} vs {col2_c} (Spearman — rank-based)")
                fig.update_layout(height=450)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: CORRELATION MATRIX (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Correlation Matrix":
    if len(numeric_cols) >= 2:
        selected_cols = st.multiselect("Select variables", options=numeric_cols, default=numeric_cols[:min(5, len(numeric_cols))])
        method = st.radio("Method", ["Pearson", "Spearman"], horizontal=True)
        
        if selected_cols and st.button("📊 Show Correlation Matrix", type="primary"):
            if method == "Pearson":
                result = active_df[selected_cols].corr(method="pearson")
            else:
                result = active_df[selected_cols].corr(method="spearman")
            
            st.dataframe(result.round(4), use_container_width=True)
            st.plotly_chart(plot_correlation_matrix(result), use_container_width=True)
            
            st.subheader("📊 P-Value Matrix")
            pvals = pd.DataFrame(np.zeros((len(selected_cols), len(selected_cols))), columns=selected_cols, index=selected_cols)
            for i, c1 in enumerate(selected_cols):
                for j, c2 in enumerate(selected_cols):
                    if i != j:
                        if method == "Pearson":
                            _, p = stats.pearsonr(active_df[c1].dropna(), active_df[c2].dropna())
                        else:
                            _, p = stats.spearmanr(active_df[c1].dropna(), active_df[c2].dropna())
                        pvals.loc[c1, c2] = p
                    else:
                        pvals.loc[c1, c2] = np.nan
            st.dataframe(pvals.round(4), use_container_width=True)
            
            log_analysis(f"Correlation Matrix ({method})", {"columns": selected_cols}, result.to_dict())
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LINEAR REGRESSION (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Linear Regression":
    if len(numeric_cols) >= 2:
        target = st.selectbox("Target (dependent)", options=numeric_cols)
        features = st.multiselect("Features (predictors)", options=[c for c in numeric_cols if c != target])
        
        if features:
            vif_result = check_multicollinearity(active_df, features)
            if "vif_table" in vif_result:
                with st.expander("🔍 Multicollinearity Check (VIF)"):
                    st.dataframe(vif_result["vif_table"], use_container_width=True, hide_index=True)
                    if vif_result["max_vif"] > 5:
                        st.warning(f"⚠️ Moderate-to-high multicollinearity detected (max VIF = {vif_result['max_vif']:.2f}). Consider removing correlated predictors.")
            
            if st.button("▶️ Run Linear Regression", type="primary"):
                result = engine.linear_regression(active_df, target, features)
                if "error" in result:
                    st.error(result["error"])
                elif "summary" in result:
                    st.dataframe(result["summary"], use_container_width=True, hide_index=True)
                    
                    if "predictions" in result and "residuals" in result:
                        st.subheader("📈 Residual Diagnostics")
                        st.plotly_chart(plot_residuals(result.get("y_true", []), result.get("predictions", [])), use_container_width=True)
                    
                    apa = generate_apa_regression(result, target, features)
                    st.subheader("📄 APA-Style Report")
                    st.code(apa, language="markdown")
                    copy_to_clipboard_button(apa, "📋 Copy APA Report")
                    
                    st.subheader("💻 Reproducible Code")
                    code_tab1, code_tab2 = st.tabs(["Python", "R"])
                    with code_tab1:
                        py_code = generate_python_snippet("Linear Regression", {"target": target, "features": features})
                        st.code(py_code, language="python")
                        copy_to_clipboard_button(py_code, "📋 Copy Python Code")
                    with code_tab2:
                        r_code = generate_r_snippet("Linear Regression", {"target": target, "features": features})
                        st.code(r_code, language="r")
                        copy_to_clipboard_button(r_code, "📋 Copy R Code")
                    
                    log_analysis("Linear Regression", {"target": target, "features": features}, result.get("summary", {}).to_dict() if hasattr(result.get("summary"), "to_dict") else {})
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: LOGISTIC REGRESSION (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Logistic Regression":
    bool_or_binary = [c for c in cat_cols if active_df[c].nunique() == 2]
    if bool_cols:
        bool_or_binary.extend(bool_cols)
    if bool_or_binary and numeric_cols:
        target = st.selectbox("Binary target", options=bool_or_binary)
        features = st.multiselect("Features (predictors)", options=numeric_cols)
        
        if features and st.button("▶️ Run Logistic Regression", type="primary"):
            result = engine.logistic_regression(active_df, target, features)
            if "error" in result:
                st.error(result["error"])
            elif "summary" in result:
                st.dataframe(result["summary"], use_container_width=True, hide_index=True)
                
                # FIXED: Corrected syntax error on key lookups
                if "pseudo_r2" in result:
                    st.metric("Pseudo R² (McFadden)", f"{result['pseudo_r2']:.4f}")
                if "accuracy" in result:
                    st.metric("Accuracy", f"{result['accuracy']:.3f}")
                
                log_analysis("Logistic Regression", {"target": target, "features": features}, result.get("summary", {}).to_dict() if hasattr(result.get("summary"), "to_dict") else {})
    else:
        st.warning("Need a binary target variable and at least 1 numeric predictor.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MULTICOLLINEARITY CHECK / VIF (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Multicollinearity Check (VIF)":
    if len(numeric_cols) >= 2:
        features = st.multiselect("Select predictors to check", options=numeric_cols, default=numeric_cols[:min(4, len(numeric_cols))])
        if len(features) >= 2 and st.button("▶️ Calculate VIF", type="primary"):
            result = check_multicollinearity(active_df, features)
            if "error" in result:
                st.error(result["error"])
            else:
                st.dataframe(result["vif_table"], use_container_width=True, hide_index=True)
                st.metric("Max VIF", f"{result['max_vif']:.2f}")
                st.markdown(f"**Interpretation**: {result['multicollinearity']} multicollinearity")
                
                fig = px.bar(result["vif_table"], x="Variable", y="VIF", color="VIF", 
                            color_continuous_scale=["green", "yellow", "red"], template="plotly_white")
                fig.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Moderate threshold")
                fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="Severe threshold")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                log_analysis("VIF Check", {"features": features}, result["vif_table"].to_dict())
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: MANN-WHITNEY U (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Mann-Whitney U":
    binary_cats_local = [c for c in cat_cols if active_df[c].nunique() == 2]
    if binary_cats_local and numeric_cols:
        group_col = st.selectbox("Group variable (2 groups)", options=binary_cats_local)
        value_col = st.selectbox("Test variable", options=numeric_cols)
        
        if st.button("▶️ Run Mann-Whitney U", type="primary"):
            result = engine.mann_whitney(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                params = {"group_col": group_col, "value_col": value_col}
                render_result_panel(result, test_name, params)
                
                fig = plot_boxplot_with_errorbars(active_df, group_col, value_col)
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Need a binary categorical and a numeric variable.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: KRUSKAL-WALLIS H (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Kruskal-Wallis H":
    if cat_cols and numeric_cols:
        group_col = st.selectbox("Group variable", options=cat_cols)
        value_col = st.selectbox("Test variable", options=numeric_cols)
        
        if st.button("▶️ Run Kruskal-Wallis", type="primary"):
            result = engine.kruskal_wallis(active_df, group_col, value_col)
            if "error" in result:
                st.error(result["error"])
            else:
                params = {"group_col": group_col, "value_col": value_col}
                render_result_panel(result, test_name, params)
                
                fig = plot_boxplot_with_errorbars(active_df, group_col, value_col)
                st.plotly_chart(fig, use_container_width=True)
                
                if result.get("significant"):
                    st.info("💡 Significant result detected. Consider running **Dunn's post-hoc test** with Bonferroni correction in Python/R for pairwise comparisons.")
    else:
        st.warning("Need at least 1 categorical and 1 numeric variable.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: WILCOXON SIGNED-RANK (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Wilcoxon Signed-Rank":
    if len(numeric_cols) >= 2:
        before = st.selectbox("Before / First measure", options=numeric_cols)
        after = st.selectbox("After / Second measure", options=numeric_cols, index=min(1, len(numeric_cols)-1))
        
        if before != after:
            if st.button("▶️ Run Wilcoxon Test", type="primary"):
                result = engine.wilcoxon_signed_rank(active_df, before, after)
                if "error" in result:
                    st.error(result["error"])
                else:
                    params = {"before": before, "after": after}
                    render_result_panel(result, test_name, params)
                    
                    fig = go.Figure()
                    diff = active_df[before] - active_df[after]
                    fig.add_trace(go.Histogram(x=diff.dropna(), nbinsx=20, marker_color="#667eea"))
                    fig.add_vline(x=0, line_dash="dash", line_color="red")
                    fig.update_layout(title=f"Distribution of Differences ({before} - {after})", template="plotly_white", height=400)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Please select two different variables.")
    else:
        st.warning("Need at least 2 numeric variables.")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: FRIEDMAN TEST (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Friedman Test":
    if len(numeric_cols) >= 3:
        measures = st.multiselect("Select 3+ related samples", options=numeric_cols, default=numeric_cols[:min(3, len(numeric_cols))])
        
        if len(measures) >= 3 and st.button("▶️ Run Friedman Test", type="primary"):
            data_matrix = active_df[measures].dropna().values.T
            stat, p = stats.friedmanchisquare(*data_matrix)
            
            col1, col2 = st.columns(2)
            col1.metric("Chi-Square", f"{stat:.4f}")
            col2.metric("P-Value", f"{p:.6f}")
            st.markdown(f"**Significant**: {'✅ Yes' if p < 0.05 else '❌ No'}")
            
            apa = f"Friedman's test indicated a {'significant' if p < 0.05 else 'non-significant'} difference across conditions, chi²({len(measures)-1}) = {stat:.2f}, p = {p:.4f}."
            st.subheader("📄 APA-Style Report")
            st.code(apa, language="markdown")
            copy_to_clipboard_button(apa, "📋 Copy APA Report")
            
            fig = px.box(active_df[measures].melt(var_name="Condition", value_name="Score"), 
                        x="Condition", y="Score", points="all", color="Condition", template="plotly_white")
            fig.update_layout(title="Friedman Test: Conditions Comparison", height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            log_analysis("Friedman Test", {"measures": measures}, {"chi2": stat, "p": p})
    else:
        st.warning("Need at least 3 numeric variables (related samples).")

# ═══════════════════════════════════════════════════════════════════════════════
# TEST: NORMALITY TEST (ENHANCED)
# ═══════════════════════════════════════════════════════════════════════════════

elif test_name == "Normality Test":
    if numeric_cols:
        col = st.selectbox("Select variable", options=numeric_cols)
        alpha = st.slider("Alpha level", 0.01, 0.10, 0.05, 0.01)
        
        if st.button("▶️ Test Normality", type="primary"):
            result = engine.test_normality(active_df, col)
            if "error" in result:
                st.error(result["error"])
            else:
                result = check_normality(active_df[col], alpha)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Statistic", result["statistic"])
                with col2:
                    st.metric("P-Value", result["p_value"])
                st.markdown(f"**Normal Distribution**: {'✅ Yes' if result['is_normal'] else '❌ No'} ({result['test']})")
                
                st.subheader("📈 Diagnostic Plots")
                qq_fig = plot_qq(active_df[col], f"Q-Q Plot: {col}")
                st.plotly_chart(qq_fig, use_container_width=True)
                
                hist_fig = px.histogram(active_df, x=col, nbins=30, template="plotly_white", title=f"Distribution of {col}")
                hist_fig.update_layout(showlegend=False, height=350)
                st.plotly_chart(hist_fig, use_container_width=True)
                
                with st.expander("🔬 Compare Normality Tests"):
                    sw_stat, sw_p = stats.shapiro(active_df[col].dropna())
                    ks_stat, ks_p = stats.kstest(active_df[col].dropna(), 'norm', args=(active_df[col].mean(), active_df[col].std()))
                    comp_df = pd.DataFrame({
                        "Test": ["Shapiro-Wilk", "Kolmogorov-Smirnov"],
                        "Statistic": [sw_stat, ks_stat],
                        "P-Value": [sw_p, ks_p],
                        "Normal?": ["✅" if sw_p > alpha else "❌", "✅" if ks_p > alpha else "❌"]
                    })
                    st.dataframe(comp_df, use_container_width=True, hide_index=True)