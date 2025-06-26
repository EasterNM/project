from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from App_Products.models import Product, ProductSupplier
from App_Purchase.models import PurchaseOrder, PurchaseOrderDetail
from App_Inventory.models import InventoryItem

class Command(BaseCommand):
    help = 'Creates draft POs for products below reorder point'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Just show what would be ordered without creating POs',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Get products with reorder point and available stock below reorder point
        low_stock_products = Product.objects.filter(
            reorder_point__gt=0
        ).annotate(
            available_stock=Count(
                'inventoryitem',
                filter=Q(inventoryitem__status=InventoryItem.Status.AVAILABLE)
            )
        ).filter(
            available_stock__lt=F('reorder_point')
        )

        if not low_stock_products.exists():
            self.stdout.write(self.style.SUCCESS('No products need reordering'))
            return

        # Group by supplier
        supplier_orders = {}

        # Process each low stock product
        for product in low_stock_products:
            # Get default supplier or skip if none
            primary_supplier = ProductSupplier.objects.filter(
                product=product, 
                is_primary_supplier=True,
                supplier__status='active'
            ).first()

            if not primary_supplier:
                self.stdout.write(
                    self.style.WARNING(
                        f'No primary supplier for product {product.name} (SKU: {product.sku})'
                    )
                )
                continue

            # Calculate order quantity
            to_order = max(0, product.reorder_point - product.available_stock)
            # Use product's reorder_quantity if set, else just order what's needed
            order_qty = product.reorder_quantity if product.reorder_quantity > 0 else to_order
            # If supplier has minimum order quantity, respect that
            if primary_supplier.minimum_order_quantity:
                order_qty = max(order_qty, primary_supplier.minimum_order_quantity)

            if dry_run:
                self.stdout.write(
                    f'Would order {order_qty} x {product.name} '
                    f'from {primary_supplier.supplier.company_name}'
                )
                continue

            # Group by supplier
            if primary_supplier.supplier.id not in supplier_orders:
                supplier_orders[primary_supplier.supplier.id] = {
                    'supplier': primary_supplier.supplier,
                    'items': []
                }
            
            supplier_orders[primary_supplier.supplier.id]['items'].append({
                'product': product,
                'quantity': order_qty,
                'unit_price': primary_supplier.unit_price
            })

        if dry_run:
            return

        # Create POs for each supplier
        try:
            with transaction.atomic():
                for supplier_id, order_data in supplier_orders.items():
                    supplier = order_data['supplier']
                    items = order_data['items']

                    # Create PO
                    po = PurchaseOrder.objects.create(
                        supplier=supplier,
                        status=PurchaseOrder.Status.DRAFT,
                        expected_delivery_date=timezone.now().date() + timezone.timedelta(days=7),
                        remarks='Auto-generated PO for low stock items'
                    )

                    # Create PO details
                    for item in items:
                        PurchaseOrderDetail.objects.create(
                            purchase_order=po,
                            product=item['product'],
                            quantity=item['quantity'],
                            unit_price=item['unit_price']
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Created PO {po.po_number} for supplier {supplier.company_name} '
                            f'with {len(items)} items'
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating POs: {str(e)}')
            )
            raise
