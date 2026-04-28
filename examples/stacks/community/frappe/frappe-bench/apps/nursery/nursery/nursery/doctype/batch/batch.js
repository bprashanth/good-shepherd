frappe.ui.form.on('Batch', {
  species: function(frm) {
    if (!frm.doc.species) {
      return;
    }

    frappe.db.get_value('Species', frm.doc.species, [
      'processing',
      'germination_time',
      'germination_percent'
    ]).then((response) => {
      const values = response.message || {};
      frm.set_value('processing', values.processing || '');
      frm.set_value('germination_time', values.germination_time || '');
      frm.set_value('germination_percent', values.germination_percent || null);
    });
  },
  refresh: function(frm) {
    // Seed one empty row for Collections to reduce confusion
    if (!frm.doc.allocations || frm.doc.allocations.length === 0) {
      frm.add_child('allocations');
      frm.refresh_field('allocations');
    }
  }
});
