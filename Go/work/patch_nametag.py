import io, sys
p = '/workspace/pdapp/src/com/seer/pdataeditor/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
orig = s

pairs = []

pairs.append(("""        nm.setSingleLine(true);
        nm.setEllipsize(TextUtils.TruncateAt.END);
        col.addView(nm);
""", """        nm.setSingleLine(true);
        nm.setEllipsize(TextUtils.TruncateAt.END);
        col.addView(nameWithTag(nm, id));
"""))

pairs.append(("""        TextView typeTag = petTypeTag(id);
        if (typeTag != null) head.addView(typeTag);

""", ""))

pairs.append(("""        col.addView(t);
        col.addView(meta);
        row.addView(col, new LinearLayout.LayoutParams(0, -2, 1f));

        TextView tag = petTypeTag(pid);
        if (tag != null) row.addView(tag);
""", """        col.addView(nameWithTag(t, pid));
        col.addView(meta);
        row.addView(col, new LinearLayout.LayoutParams(0, -2, 1f));
"""))

pairs.append(("""                row.addView(nm, new LinearLayout.LayoutParams(0, -2, 1f));

                // 类型标签：创建时会按特攻/攻击种族值自动取性格与学习力
                TextView tag = petTypeTag(e[0]);
                if (tag != null) row.addView(tag);
""", """                nm.setMaxWidth(nameMaxWidth());
                row.addView(nm, new LinearLayout.LayoutParams(-2, -2));

                // 类型标签紧跟名称；右侧「已拥有」与编号保持右对齐
                TextView tag = petTypeTag(e[0]);
                if (tag != null) row.addView(tag);
                row.addView(new View(this), new LinearLayout.LayoutParams(0, 1, 1f));
"""))

pairs.append(("""        lp.rightMargin = dp(6);
        tag.setLayoutParams(lp);
        return tag;
    }
""", """        lp.rightMargin = dp(6);
        tag.setLayoutParams(lp);
        return tag;
    }

    /** 名称可用的最大宽度：给编号、箭头与类型标签留出空间。 */
    private int nameMaxWidth() {
        int w = getResources().getDisplayMetrics().widthPixels - dp(190);
        return Math.max(dp(80), w);
    }

    /** 名称与其后的类型标签：名字过长时截断，标签始终紧跟名称并完整显示。 */
    private LinearLayout nameWithTag(TextView nm, String id) {
        LinearLayout line = new LinearLayout(this);
        line.setOrientation(LinearLayout.HORIZONTAL);
        line.setGravity(Gravity.CENTER_VERTICAL);
        nm.setMaxWidth(nameMaxWidth());
        line.addView(nm, new LinearLayout.LayoutParams(-2, -2));
        TextView tag = petTypeTag(id);
        if (tag != null) line.addView(tag);
        return line;
    }
"""))

for old, new in pairs:
    if s.count(old) != 1:
        print('FAIL count=%d for: %r' % (s.count(old), old[:60]))
        sys.exit(1)
    s = s.replace(old, new)

io.open(p, 'w', encoding='utf-8').write(s)
print('patched', len(orig), '->', len(s))
