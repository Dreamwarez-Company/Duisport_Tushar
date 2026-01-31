from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    quotation_terms = fields.Html(
        string="Terms & Conditions",
        help="Quotation Terms & Conditions",
        default="""
        <p><strong>Price:</strong> The quoted price is exclusive of GST.</p>

        <p><strong>Transportation:</strong>
        Freight will be charged Extra at the Actual if the truck freight cost is not matched due to less qty.</p>

        <p><strong>MOQ:</strong>
        Rates are valid only if order received as per the MOQ.</p>

        <p><strong>Inventory:</strong>
        Stock will be maintained based on the schedule given – 15 to 20% extra – if there is any change in plan or
        specification or short closure of the order, you need to bear the full cost of material kept in Inventory –
        In the case of SFG / FG parts.</p>

        <p>For the plain boards, it can be mutually discussed and resolved depending on the usability of the boards.</p>

        <p><strong>GST:</strong> Extra as applicable depending on the product.</p>

        <p><strong>HSN Code:</strong><br/>
        Corrugated box/board only – 48191010<br/>
        Corrugated box with pallet – 48191010<br/>
        Wood / Plywood box/pallet – 44151000
        </p>

        <p><strong>Lead Time:</strong>
        First set 10 to 15 days – 3 months tentative schedule to be shared by you,
        2nd set onwards based on the schedule shared by you.</p>

        <p><strong>Additional Process / Treatment cost:</strong>
        Extra as applicable – will be processed and chargeable as mutually agreed upon.</p>

        <p><strong>Quotation Validity:</strong> 7 days.</p>

        <p><strong>Payment Terms:</strong>
        Advance or 30 days credit period from date of Invoice.</p>

        <p><strong>General Note:</strong><br/>
        1. As per ISPM-15 standard, Duisport does not guarantee for mold and fungus formation due to Increase 
        in moisture levels in wood/Plywood (Naturally due to atmospheric conditions / due to water splash or 
        getting wet in water through any kind of source).<br/>
        2. Plywood and corrugated boards are exempted from fumigation / heat treatment.<br/>
        3. If market rates fluctuate, then we have to revise the rates accordingly on mutual concern.<br/>
        4. If there is any additional process or design change made prices will be revised accordingly.>br/>
        5.The outsourced items supplied or referred by us are as per the Standards shared by the Suppliers terms 
        and conditions.  Any discrepancy arising from this will have to be referred and taken up with the 
        concerned suppliers as per their terms and conditions.<br/>
        6.In-house Inspection reports will be shared for every batch, if the material test certificate required 
        from the 3rd party Lab, the cost for the same will be charged @ actual + the material cost + freight + taxes.
        </p>

        <p><strong>For Duisport Packing Logistics India Pvt. Ltd.</strong><br/>
        <strong>Khushbu Baiswar</strong><br/>
        Customer Support<br/>
        Mobile No.: +91 7408247865</p>
        """
    )
