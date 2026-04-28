frappe.ui.form.on('Species', {
  accepted_name: function(frm) {
    if (!frm.doc.accepted_name) {
      return;
    }
    const parts = frm.doc.accepted_name.trim().split(/\s+/);
    const genus = parts[0] || '';
    const species = parts[1] || '';
    const code = (genus.substring(0, 3) + species.substring(0, 3)).toUpperCase();
    frm.set_value('species_code', code || 'SPC');
  }
});
