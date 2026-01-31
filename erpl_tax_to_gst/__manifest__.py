# -*- coding: utf-8 -*-
#############################################################################
#
#    ERP Labz
#
#    Copyright (C) 2024-TODAY ERP Labz(<https://www.erplabz.com>).
#    Author: ERP Labz
#    Maintainer: ERP Labz
#
#    You can modify it under the terms of the GNU LGPL-3
#    (LGPL-3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL-3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL-3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
{
    'name': 'ERP Labz Tax to GST',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Convert and rename taxes to GST format',
    'description': """
ERP Labz Tax to GST
===================
This module allows you to convert and rename taxes to GST (Goods and Services Tax) 
format in Odoo, making it easy to update your tax structure to comply with GST 
requirements, especially for Indian businesses.

Features:
---------
* Convert tax names from "Tax" to "GST"
* Rename tax groups to GST format
* Update tax descriptions to GST terminology
* Bulk conversion of all taxes
* Selective conversion of specific taxes
* Preview changes before applying
* Backup and restore functionality
* Compatible with Odoo 17, 18, and 19

Use Cases:
----------
* Migrating from old tax system to GST
* Updating tax terminology to GST format
* Standardizing tax names across the system
* Compliance with GST regulations
    """,
    'author': 'ERP Labz',
    'company': 'ERP Labz',
    'maintainer': 'ERP Labz',
    'website': 'https://www.erplabz.com',
    'license': 'LGPL-3',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tax_to_gst_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/banner.svg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}

