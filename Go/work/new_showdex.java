    private void showPetDex() {
        showPetDex(0);
    }

    /** 精灵 / 技能图鉴。mode：0 = 精灵，1 = 技能。 */
    private void showPetDex(final int initialMode) {
        loadDex();
        loadSkills();
        final Dialog dlg = new Dialog(this);
        dlg.requestWindowFeature(Window.FEATURE_NO_TITLE);

        FrameLayout root = new FrameLayout(this);
        root.setPadding(dp(10), dp(12), dp(10), dp(12));

        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setBackground(roundStroke(0xFF0B1424, C_LINE, 16, 1));
        card.setPadding(dp(14), dp(12), dp(14), dp(8));
        root.addView(card, new FrameLayout.LayoutParams(-1, -1));

        // 标题栏
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        View accent = new View(this);
        accent.setBackground(round(C_GOLD, 2));
        LinearLayout.LayoutParams alp = new LinearLayout.LayoutParams(dp(3), dp(16));
        alp.rightMargin = dp(8);
        head.addView(accent, alp);

        final TextView title = new TextView(this);
        title.setText("精灵图鉴");
        title.setTextSize(17);
        title.setTextColor(C_TEXT);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        head.addView(title);

        final TextView count = new TextView(this);
        count.setTextSize(10);
        count.setTextColor(C_TEXT_FAINT);
        LinearLayout.LayoutParams clp = new LinearLayout.LayoutParams(-2, -2);
        clp.leftMargin = dp(8);
        head.addView(count, clp);

        head.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));

        TextView close = new TextView(this);
        close.setText("关闭");
        close.setTextSize(13);
        close.setTextColor(C_GOLD);
        close.setPadding(dp(12), dp(6), dp(4), dp(6));
        close.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                dlg.dismiss();
            }
        });
        head.addView(close);
        card.addView(head, new LinearLayout.LayoutParams(-1, -2));

        // 模式切换：精灵 / 技能
        LinearLayout tabs = new LinearLayout(this);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        tabs.setBackground(roundStroke(0x66071022, C_LINE, 10, 1));
        tabs.setPadding(dp(3), dp(3), dp(3), dp(3));
        LinearLayout.LayoutParams tabsLp = new LinearLayout.LayoutParams(-1, -2);
        tabsLp.topMargin = dp(10);
        card.addView(tabs, tabsLp);

        final TextView tabPet = new TextView(this);
        tabPet.setText("精灵");
        tabPet.setTextSize(12);
        tabPet.setGravity(Gravity.CENTER);
        tabPet.setPadding(0, dp(6), 0, dp(6));
        tabs.addView(tabPet, new LinearLayout.LayoutParams(0, -2, 1f));

        final TextView tabSkill = new TextView(this);
        tabSkill.setText("技能");
        tabSkill.setTextSize(12);
        tabSkill.setGravity(Gravity.CENTER);
        tabSkill.setPadding(0, dp(6), 0, dp(6));
        tabs.addView(tabSkill, new LinearLayout.LayoutParams(0, -2, 1f));

        // 搜索框：精灵按名称 / ID，技能按名称 / 描述 / ID
        final EditText search = new EditText(this);
        search.setHint("搜索精灵名称或 ID");
        search.setHintTextColor(C_TEXT_FAINT);
        search.setTextColor(C_TEXT);
        search.setTextSize(13);
        search.setSingleLine(true);
        search.setBackground(fieldBg());
        search.setPadding(dp(12), 0, dp(12), 0);
        search.setInputType(InputType.TYPE_CLASS_TEXT);
        search.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        LinearLayout.LayoutParams slp = new LinearLayout.LayoutParams(-1, dp(42));
        slp.topMargin = dp(8);
        card.addView(search, slp);

        // 属性筛选：精灵、技能各一套
        final List<String> petTypes = new ArrayList<>();
        petTypes.add("全部");
        for (int i = 0; i < dexPets.length(); i++) {
            String t = dexPets.optJSONObject(i).optString("t", "未知");
            if (!petTypes.contains(t)) petTypes.add(t);
        }
        final List<String> skillTypes = new ArrayList<>();
        skillTypes.add("全部");
        for (int i = 0; i < dexSkills.length(); i++) {
            String t = dexSkills.optJSONObject(i).optString("t", "未知");
            if (!skillTypes.contains(t)) skillTypes.add(t);
        }

        final int[] mode = {initialMode == 1 ? 1 : 0};
        final String[] petSel = {"全部"};
        final String[] skillSel = {"全部"};
        final Runnable[] refresh = new Runnable[1];
        final Runnable chipChanged = new Runnable() {
            public void run() {
                if (refresh[0] != null) refresh[0].run();
            }
        };
        final HorizontalScrollView petChips = dexChipRow(petTypes, petSel, chipChanged);
        final HorizontalScrollView skillChips = dexChipRow(skillTypes, skillSel, chipChanged);
        LinearLayout.LayoutParams hlp = new LinearLayout.LayoutParams(-1, -2);
        hlp.topMargin = dp(8);
        card.addView(petChips, hlp);
        LinearLayout.LayoutParams hlp2 = new LinearLayout.LayoutParams(-1, -2);
        hlp2.topMargin = dp(8);
        card.addView(skillChips, hlp2);
        skillChips.setVisibility(View.GONE);

        // 精灵列表
        final List<JSONObject> filteredPets = new ArrayList<>();
        final BaseAdapter petAdapter = new BaseAdapter() {
            public int getCount() {
                return filteredPets.size();
            }

            public Object getItem(int p) {
                return filteredPets.get(p);
            }

            public long getItemId(int p) {
                return p;
            }

            public View getView(int p, View cv, ViewGroup parent) {
                final JSONObject pet = filteredPets.get(p);
                String id = pet.optString("i");
                String nm = pet.optString("n");
                String ty = pet.optString("t", "未知");
                int col = dexTypeColor(ty);

                LinearLayout row = new LinearLayout(MainActivity.this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);
                row.setMinimumHeight(dp(58));
                row.setPadding(dp(8), dp(6), dp(8), dp(6));
                row.setBackground(pressable(round(0x00000000, 10), 0x1FFFFFFF));

                LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(dp(42), dp(42));
                ilp.rightMargin = dp(10);
                row.addView(dexIconView(id, nm, col, 1), ilp);

                LinearLayout midCol = new LinearLayout(MainActivity.this);
                midCol.setOrientation(LinearLayout.VERTICAL);
                TextView name = new TextView(MainActivity.this);
                name.setText(nm);
                name.setTextSize(14);
                name.setTextColor(C_TEXT);
                name.setSingleLine(true);
                name.setEllipsize(TextUtils.TruncateAt.END);
                midCol.addView(name);
                TextView sub = new TextView(MainActivity.this);
                sub.setText(ty);
                sub.setTextSize(10);
                sub.setTextColor(C_TEXT_FAINT);
                sub.setSingleLine(true);
                midCol.addView(sub);
                row.addView(midCol, new LinearLayout.LayoutParams(0, -2, 1f));

                LinearLayout rightCol = new LinearLayout(MainActivity.this);
                rightCol.setOrientation(LinearLayout.VERTICAL);
                rightCol.setGravity(Gravity.RIGHT);
                TextView idv = new TextView(MainActivity.this);
                idv.setText("#" + id);
                idv.setTextSize(10);
                idv.setTextColor(C_TEXT_FAINT);
                idv.setTypeface(Typeface.MONOSPACE);
                rightCol.addView(idv);
                if (pet.optInt("d", 1) == 0) {
                    TextView nx = new TextView(MainActivity.this);
                    nx.setText("未收录");
                    nx.setTextSize(9);
                    nx.setTextColor(C_AMBER);
                    rightCol.addView(nx);
                }
                row.addView(rightCol);
                return row;
            }
        };

        // 技能列表
        final List<JSONObject> filteredSkills = new ArrayList<>();
        final BaseAdapter skillAdapter = new BaseAdapter() {
            public int getCount() {
                return filteredSkills.size();
            }

            public Object getItem(int p) {
                return filteredSkills.get(p);
            }

            public long getItemId(int p) {
                return p;
            }

            public View getView(int p, View cv, ViewGroup parent) {
                final JSONObject sk = filteredSkills.get(p);
                int sid = sk.optInt("i");
                String nm = sk.optString("n");
                String ty = sk.optString("t", "未知");
                int cat = sk.optInt("c");
                int power = sk.optInt("p");
                int pp = sk.optInt("pp");
                int col = dexTypeColor(ty);
                String catName = dexCategory(cat);

                LinearLayout row = new LinearLayout(MainActivity.this);
                row.setOrientation(LinearLayout.HORIZONTAL);
                row.setGravity(Gravity.CENTER_VERTICAL);
                row.setMinimumHeight(dp(58));
                row.setPadding(dp(8), dp(6), dp(8), dp(6));
                row.setBackground(pressable(round(0x00000000, 10), 0x1FFFFFFF));

                TextView ic = new TextView(MainActivity.this);
                ic.setText(catName.length() > 0 ? catName.substring(0, 1) : "?");
                ic.setTextSize(15);
                ic.setTextColor(col);
                ic.setGravity(Gravity.CENTER);
                ic.setBackground(roundStroke(0x22FFFFFF | (col & 0x00FFFFFF),
                        col & 0x66FFFFFF, 10, 1));
                LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(dp(42), dp(42));
                ilp.rightMargin = dp(10);
                row.addView(ic, ilp);

                LinearLayout midCol = new LinearLayout(MainActivity.this);
                midCol.setOrientation(LinearLayout.VERTICAL);
                TextView name = new TextView(MainActivity.this);
                name.setText(nm);
                name.setTextSize(14);
                name.setTextColor(C_TEXT);
                name.setSingleLine(true);
                name.setEllipsize(TextUtils.TruncateAt.END);
                midCol.addView(name);
                TextView sub = new TextView(MainActivity.this);
                String meta = ty + (catName.length() > 0 ? " · " + catName : "")
                        + (power > 0 ? " · 威力 " + power : "") + " · PP " + pp;
                sub.setText(meta);
                sub.setTextSize(10);
                sub.setTextColor(C_TEXT_FAINT);
                sub.setSingleLine(true);
                midCol.addView(sub);
                row.addView(midCol, new LinearLayout.LayoutParams(0, -2, 1f));

                TextView idv = new TextView(MainActivity.this);
                idv.setText("#" + sid);
                idv.setTextSize(10);
                idv.setTextColor(C_TEXT_FAINT);
                idv.setTypeface(Typeface.MONOSPACE);
                row.addView(idv);
                return row;
            }
        };

        final ListView petList = new ListView(this);
        petList.setDivider(null);
        petList.setDividerHeight(0);
        petList.setAdapter(petAdapter);
        petList.setPadding(0, dp(2), 0, 0);

        final ListView skillList = new ListView(this);
        skillList.setDivider(null);
        skillList.setDividerHeight(0);
        skillList.setAdapter(skillAdapter);
        skillList.setPadding(0, dp(2), 0, 0);
        skillList.setVisibility(View.GONE);

        // 详情页（不透明背景，避免与列表叠加）
        final ScrollView detail = new ScrollView(this);
        detail.setVisibility(View.GONE);
        detail.setFillViewport(true);
        detail.setBackgroundColor(0xFF0B1424);

        final ScrollView skillDetail = new ScrollView(this);
        skillDetail.setVisibility(View.GONE);
        skillDetail.setFillViewport(true);
        skillDetail.setBackgroundColor(0xFF0B1424);

        final FrameLayout content = new FrameLayout(this);
        content.addView(petList, new FrameLayout.LayoutParams(-1, -1));
        content.addView(skillList, new FrameLayout.LayoutParams(-1, -1));
        content.addView(detail, new FrameLayout.LayoutParams(-1, -1));
        content.addView(skillDetail, new FrameLayout.LayoutParams(-1, -1));
        LinearLayout.LayoutParams ctlp = new LinearLayout.LayoutParams(-1, 0, 1f);
        ctlp.topMargin = dp(8);
        card.addView(content, ctlp);

        final View[] layers = {petList, skillList, detail, skillDetail};
        final Runnable hideLayers = new Runnable() {
            public void run() {
                for (int i = 0; i < layers.length; i++) layers[i].setVisibility(View.GONE);
            }
        };

        final SkillOpen[] sopen = new SkillOpen[1];
        final PetOpen[] popen = new PetOpen[1];

        popen[0] = new PetOpen() {
            public void open(final JSONObject pet, String backLabel, final View origin) {
                hideLayers.run();
                buildDexDetail(detail, pet, backLabel, new Runnable() {
                    public void run() {
                        hideLayers.run();
                        origin.setVisibility(View.VISIBLE);
                    }
                }, sopen[0]);
                detail.scrollTo(0, 0);
                detail.setVisibility(View.VISIBLE);
                hideKeyboard(search);
            }
        };

        sopen[0] = new SkillOpen() {
            public void open(int sid, final View origin) {
                JSONObject sk = findSkill(sid);
                if (sk == null) return;
                hideLayers.run();
                buildSkillDetail(skillDetail, sk, "‹ 返回精灵", new Runnable() {
                    public void run() {
                        hideLayers.run();
                        origin.setVisibility(View.VISIBLE);
                    }
                }, popen[0]);
                skillDetail.scrollTo(0, 0);
                skillDetail.setVisibility(View.VISIBLE);
            }
        };

        refresh[0] = new Runnable() {
            public void run() {
                if (mode[0] == 0) {
                    filterDex(filteredPets, search.getText().toString(), petSel[0]);
                    petAdapter.notifyDataSetChanged();
                    count.setText("共 " + filteredPets.size() + " 只");
                } else {
                    filterSkills(filteredSkills, search.getText().toString(), skillSel[0]);
                    skillAdapter.notifyDataSetChanged();
                    count.setText("共 " + filteredSkills.size() + " 个技能");
                }
            }
        };

        final Runnable[] applyMode = new Runnable[1];
        applyMode[0] = new Runnable() {
            public void run() {
                boolean petMode = mode[0] == 0;
                title.setText(petMode ? "精灵图鉴" : "技能图鉴");
                tabPet.setTextColor(petMode ? 0xFF1A1406 : C_TEXT_DIM);
                tabPet.setBackground(petMode ? roundStroke(C_GOLD, C_GOLD, 8, 1)
                        : round(0x00000000, 8));
                tabSkill.setTextColor(petMode ? C_TEXT_DIM : 0xFF1A1406);
                tabSkill.setBackground(petMode ? round(0x00000000, 8)
                        : roundStroke(C_GOLD, C_GOLD, 8, 1));
                search.setHint(petMode ? "搜索精灵名称或 ID" : "搜索技能名 / 描述 / ID");
                petChips.setVisibility(petMode ? View.VISIBLE : View.GONE);
                skillChips.setVisibility(petMode ? View.GONE : View.VISIBLE);
                hideLayers.run();
                if (petMode) petList.setVisibility(View.VISIBLE);
                else skillList.setVisibility(View.VISIBLE);
                refresh[0].run();
            }
        };

        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int b, int c) {
            }

            public void onTextChanged(CharSequence s, int a, int b, int c) {
            }

            public void afterTextChanged(Editable e) {
                if (refresh[0] != null) refresh[0].run();
            }
        });

        tabPet.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (mode[0] == 0) return;
                mode[0] = 0;
                search.setText("");
                applyMode[0].run();
            }
        });

        tabSkill.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                if (mode[0] == 1) return;
                mode[0] = 1;
                search.setText("");
                applyMode[0].run();
            }
        });

        petList.setOnItemClickListener(new android.widget.AdapterView.OnItemClickListener() {
            public void onItemClick(android.widget.AdapterView<?> av, View v, int p, long lid) {
                hideLayers.run();
                buildDexDetail(detail, filteredPets.get(p), "‹ 返回图鉴", new Runnable() {
                    public void run() {
                        hideLayers.run();
                        petList.setVisibility(View.VISIBLE);
                    }
                }, sopen[0]);
                detail.scrollTo(0, 0);
                detail.setVisibility(View.VISIBLE);
                hideKeyboard(search);
            }
        });

        skillList.setOnItemClickListener(new android.widget.AdapterView.OnItemClickListener() {
            public void onItemClick(android.widget.AdapterView<?> av, View v, int p, long lid) {
                hideLayers.run();
                buildSkillDetail(skillDetail, filteredSkills.get(p), "‹ 返回技能列表",
                        new Runnable() {
                            public void run() {
                                hideLayers.run();
                                skillList.setVisibility(View.VISIBLE);
                            }
                        }, popen[0]);
                skillDetail.scrollTo(0, 0);
                skillDetail.setVisibility(View.VISIBLE);
                hideKeyboard(search);
            }
        });

        applyMode[0].run();

        Window w = dlg.getWindow();
        if (w != null) {
            w.setBackgroundDrawable(new ColorDrawable(0));
            w.setLayout(WindowManager.LayoutParams.MATCH_PARENT, WindowManager.LayoutParams.MATCH_PARENT);
            WindowManager.LayoutParams at = w.getAttributes();
            at.dimAmount = 0.72f;
            at.flags |= WindowManager.LayoutParams.FLAG_DIM_BEHIND;
            w.setAttributes(at);
            w.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        }
        dlg.setContentView(root);
        dlg.show();
    }
