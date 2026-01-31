from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # ---------------------------------------------------------
    # Logistics / Reference Fields
    # ---------------------------------------------------------
    other_references = fields.Char(string="Other References")
    dispatched_through = fields.Char(string="Dispatched through")
    destination = fields.Char(string="Destination")
    terms_of_delivery = fields.Char(string="Terms of Delivery")

    # ---------------------------------------------------------
    # Ship To / Consignee Fields
    # ---------------------------------------------------------
    ship_to_address = fields.Text(
        string="Ship To",
        help="Consignee / Ship To Address"
    )

    ship_to_name = fields.Char(string="Consignee (Ship to)")
    ship_to_street = fields.Char(string="Address Line 1")
    ship_to_street2 = fields.Char(string="Address Line 2")
    ship_to_city = fields.Char(string="City")
    ship_to_state_id = fields.Many2one(
        'res.country.state',
        string="State"
    )
    ship_to_zip = fields.Char(string="ZIP")
    ship_to_gstin = fields.Char(string="GSTIN/UIN")

    # ---------------------------------------------------------
    # Default Values (Company Address → Ship To)
    # ---------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company

        res.setdefault('ship_to_name', company.name)
        res.setdefault('ship_to_street', company.street)
        res.setdefault('ship_to_street2', company.street2)
        res.setdefault('ship_to_city', company.city)
        res.setdefault(
            'ship_to_state_id',
            company.state_id.id if company.state_id else False
        )
        res.setdefault('ship_to_zip', company.zip)
        res.setdefault('ship_to_gstin', company.vat)

        return res

    # ---------------------------------------------------------
    # Commercial Terms & Conditions (DO NOT MODIFY CONTENT)
    # ---------------------------------------------------------
    commercial_terms = fields.Html(
        string="Commercial Terms & Conditions",
        help="Annex-1 Commercial Terms and Conditions",
        default="""
        <h3 style="text-align:center;"><strong>Annex-1</strong></h3>
        <h3 style="text-align:center;"><strong>COMMERCIAL TERMS AND CONDITIONS</strong></h3>

        <p><strong><u>1. ORDER ACCEPTANCE</u></strong></p>
        <p>
        1.1 Kindly send us your Order Acceptance within 2 working days of receipt of this Purchase Order.<br/>
        If we do not receive your Order Acceptance within the mentioned period,<br/>
        this Purchase Order and the Terms and Conditions mentioned herein<br/>
        shall be deemed unconditionally accepted by you.
        </p>

        <p><strong><u>2. PRICE BASIS</u></strong></p>
        <p>2.1 The above prices are Ex Your Works.</p>
        <p>2.2 Currency shall be Indian Rupees.</p>
        <p>
        2.3 The above prices will remain firm and final till the complete execution
        of supplies of the entire material against the PO.
        </p>

        <p><strong><u>3. TRANSIT INSURANCE</u></strong></p>
        <p>3.1 Its Vendor Responsibility.</p>

        <p><strong><u>4. L.D. CLAUSE FOR DELAY IN DELIVERY</u></strong></p>
        <p>
        4.1 L.D. clause at 5% from agreed date of delivery for 2 weeks delay,
        10% from 2 weeks to 4 weeks delay and 20% for further delay,
        in case you do not supply material on or before above-mentioned date.
        </p>

        <p><strong><u>5. DRAWING & DOCUMENTS TO BE FURNISHED FOR APPROVAL OF PURCHASER</u></strong></p>
        <p>5.1 Datasheets duly filled up.</p>
        <p>5.2 G.A Drawing with complete dimensions, shipping weight etc.</p>
        <p>5.3 QAP.</p>
        <p>5.4 Manufacturing Schedule.</p>
        <p>5.5 Billing Break up.</p>
        <p>5.6 Material Test Certificate / PDI reports.</p>

        <p><strong><u>6. RISK PURCHASE CLAUSE</u></strong></p>
        <p>
        6.1 DPL is at its sole liberty to purchase similar equipment for the purpose intended
        while ordering this material on you from any other source whether indigenous or foreign,
        at the risk and cost of the supplier (or) in case:
        </p>
        <p>6.1.1 The Supplier fails to start execution within the accepted delivery schedule to complete the job</p>
        <p>6.1.2 The progress of Manufacturing is not enough to complete the supplies within the accepted delivery schedule</p>
        <p>6.1.3 The material in manufacturing is not likely to meet the Specification, Quality and Aesthetics standards</p>
        <p>6.1.4 If the Supplier delays the supplies partially or fully</p>
        <p>6.1.5 If the Supplied item does not conform to the Specification, Quality and Aesthetics standards as per approved documents.</p>
        <p>6.1.6 The Supplied items are not suitable for the intended purpose or it is not performing the way acceptable to us or the end user </p>
        <p>6.1.7 Supplier shall be given ample opportunities to remedy such eventualities, before rights under this clause is exercised </p>

        <p><strong><u>7. REJECTION OF MATERIALS</u></strong></p>
        <p>
        7.1 Rejection of materials, if any, shall be taken by the supplier and all the costs so
        incurred shall be borne by the supplier. Such rejected material shall be at supplier’s
        risk from the time of rejection and DPL shall not be liable for any shortages/quality
        deterioration of the item.
        </p>

        <p><strong><u>8. GUARANTEES & LIABILITY</u></strong></p>
        <p>
        8.1 The Supplier guarantees that all Supplies delivered comply with the specifications
        provided by the Company as well as fit for the particular purpose for which they are
        intended. Moreover, the Supplier guarantees that the Supplies comply with the laws,
        regulations and other provisions that apply in the country of their destination. The
        Supplier shall proceed to replace non-conforming or defective Supplies as quickly as
        possible in consideration of the Companies obligations to its customers. The Supplier
        also commits to compensate the Company for all expenses and direct or indirect
        consequences resulting from the non-conformity or defectiveness. The Company
        reserves the right to implead the Supplier for any defect detected during checking,
        even if the defective Supplies have already undergone factory processing, and/or even
        if the corresponding invoices have already been paid. Any non-conforming or defective
        Supplies shall be removed by the Supplier within a period fixed by the Company, failing
        which it will be returned to the Supplier at the sole cost of the latter. The Supplies shall
        be guaranteed for Twelve (12) months starting from the date of their delivery to the
        Company, except in the case of a longer period of guarantee of which the Supplier
        shall have been informed.
        </p>
        <p>
        8.2 Guaranty, Warranty certificate & Product Manuals should be submitted with Machinery
        </p>

        <p><strong><u>9. INVOICE, CHALLAN & TRANSIT DOCUMENTS</u></strong></p>
        <p>
        9.1 One original set of invoices cum gate pass, challan, inspection and test certificate,
        warranty and guarantee certificates and other transit documents along with a full set of
        copies shall be sent along with the consignment
        </p>
        <p>
        9.2 Please quote our Purchase Order number, latest revision number & date and part / item
        code number on your challan & invoices along with correct description. Kindly note if the
        said requirement is not complied with, payment will be delayed.
        </p>
        <p>
        9.3 Material should be dispatch after the clearance from the Duisport Packing India Pvt. Ltd
        </p>

        <p><strong><u>10. QUALITY PARAMETERS</u></strong></p>
        <p>10.1 No rust on the stainless steel or iron parts.</p>
        <p>10.2 All parts which should be painted properly without any spot marks.</p>
        <p>10.3 Total Final rates should be based on actual Measurement which DPL team will verify after completion of work.</p>
        <p>10.4 quality of all items needs to be ensured like thickness of AL partition , glass , board , false ceiling etc etc</p>
        <p>10.5 PUF panels for Sound proofing should be taken care properly as there should be no outside noise and we should get
        peace to sit inside and work accordingly, This has to be ensured.</p>
        <p>10.6 quality of all hardware and joining nut , bolt, hooks , fasteners should be ensure and they should be galvanized.</p>

        <p><strong><u>11. DISPUTES / ARBITRATION</u></strong></p>
        <p>
        11.1 In the event of any disputes or disagreement in the interpretation of these terms or
        dispute arising in executing the contract, the same shall be resolved through arbitration
        as provided under provision of Arbitration & Conciliation (Amendment) Act, 2015.
        </p>
        <p>11.2 The place of arbitration shall be Pune India.</p>
        <p>11.3 All disputes are subject to Pune Jurisdiction.</p>

        <p><strong><u>12. FORCE MAJEURE</u></strong></p>
        <p>
        If at any time during the continuance of the contract the performance in part or whole, or any obligations under this
        contract is prevented or delayed by a state of force majeure war, civil commotion, sabotage, fire, flood, earthquake,
        explosion, epidemic or such acts of God. The delivery period as given in clause 8 herein above will be subject to such
        extensions as may be necessary in the event of occurrences of any of the events mentioned herein. The Onus in providing
        documentary evidence for proving the existence of such eventuality shall be on the Supplier
        </p>

        <p><strong><u>13. GENERAL</u></strong></p>
        <p>
        13.1 The terms & conditions mentioned above will prevail unless otherwise stated in the P.O
        Please quote our Purchase Order number, latest revision number and date (if any) and part/item code number on your drawings,
        challans, invoices and other documents to avoid delay in processing.
        </p>
        """
    )
