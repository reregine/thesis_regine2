# services/popularity_service.py
from datetime import datetime, timedelta
from sqlalchemy import func, and_, text
from app.extension import db
from app.models.admin import ProductPopularity

class ProductPopularityService:
    @staticmethod
    def initialize_on_startup():
        """Initialize all popularity data when application starts - ULTRA SIMPLE"""
        try:
            from app.models.admin import ProductPopularity, IncubateeProduct, Incubatee
            
            print("🚀 Initializing product popularity data on startup...")
            
            # 1. Just create missing records and skip the complex recalculation
            products_without_popularity = db.session.query(IncubateeProduct).join(
                Incubatee, IncubateeProduct.incubatee_id == Incubatee.incubatee_id
            ).filter(
                Incubatee.is_approved == True,
                ~IncubateeProduct.product_id.in_(
                    db.session.query(ProductPopularity.product_id)
                )
            ).all()
            
            for product in products_without_popularity:
                popularity = ProductPopularity(
                    product_id=product.product_id,
                    incubatee_id=product.incubatee_id,
                    weekly_sold=0,
                    monthly_customers=0,
                    weekly_revenue=0.00,
                    monthly_revenue=0.00,
                    total_revenue=0.00,
                    week_start_date=datetime.now().date(),
                    month_start_date=datetime.now().replace(day=1).date(),
                    last_updated=datetime.utcnow()
                )
                db.session.add(popularity)
                print(f"✅ Created popularity record for product {product.product_id}")
            
            db.session.commit()
            
            # 2. DON'T recalculate on startup - let it build from reservations
            print("ℹ️ Skipping full recalculation - data will build from reservations")
            
            # 3. Just update rankings for existing data
            ProductPopularityService.update_product_rankings()
            
            print("🎉 Product popularity initialization complete!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error initializing popularity on startup: {str(e)}")

    @staticmethod
    def update_from_reservation(reservation):
        """Update popularity stats when a reservation is completed - SIMPLE & RELIABLE"""
        try:
            from app.models.admin import ProductPopularity, IncubateeProduct, SalesReport
            
            if reservation.status != 'completed':
                return False
            
            # Get the sales report
            sales_report = SalesReport.query.filter_by(
                reservation_id=reservation.reservation_id
            ).first()
            
            if not sales_report:
                print(f"⚠️ No sales report found for reservation {reservation.reservation_id}")
                return False
            
            product = IncubateeProduct.query.get(reservation.product_id)
            if not product:
                return False
            
            # Get or create popularity record
            popularity = ProductPopularity.query.filter_by(
                product_id=reservation.product_id
            ).first()
            
            if not popularity:
                popularity = ProductPopularity(
                    product_id=reservation.product_id,
                    incubatee_id=product.incubatee_id,
                    weekly_sold=0,
                    monthly_sold=0,
                    total_sold=0,
                    weekly_revenue=0.00,
                    monthly_revenue=0.00,
                    total_revenue=0.00,
                    weekly_customers=0,
                    monthly_customers=0,
                    total_customers=0,
                    week_start_date=datetime.now().date(),
                    month_start_date=datetime.now().replace(day=1).date(),
                    last_updated=datetime.utcnow()
                )
                db.session.add(popularity)
                db.session.commit()  # Commit immediately for new record
            
            # Get current period dates
            current_date = datetime.now().date()
            current_week_start = current_date - timedelta(days=current_date.weekday())
            current_month_start = current_date.replace(day=1)
            
            # Update stats - SIMPLE INCREMENTAL UPDATES
            if sales_report.sale_date >= current_week_start:
                popularity.weekly_sold += sales_report.quantity
                popularity.weekly_revenue += float(sales_report.total_price)
            
            if sales_report.sale_date >= current_month_start:
                popularity.monthly_sold += sales_report.quantity
                popularity.monthly_revenue += float(sales_report.total_price)
            
            popularity.total_sold += sales_report.quantity
            popularity.total_revenue += float(sales_report.total_price)
            
            # Update customer counts (this is the only complex part)
            ProductPopularityService._update_customer_counts_simple(reservation.product_id)
            
            popularity.last_updated = datetime.utcnow()
            
            db.session.commit()
            
            print(f"📈 Updated popularity for product {reservation.product_id}: "
                f"+{sales_report.quantity} units, +₱{sales_report.total_price}")
            
            # Update rankings
            ProductPopularityService.update_product_rankings()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating popularity from reservation: {str(e)}")
            return False

    # ADD THIS METHOD TO FIX THE ERROR
    @staticmethod
    def update_product_popularity(reservation):
        """Alias method for backward compatibility"""
        return ProductPopularityService.update_from_reservation(reservation)

    @staticmethod
    def _update_customer_counts_simple(product_id):
        """Update customer counts for a product - SIMPLE VERSION"""
        from app.models.admin import SalesReport
        
        current_date = datetime.now().date()
        current_week_start = current_date - timedelta(days=current_date.weekday())
        current_month_start = current_date.replace(day=1)
        
        # Get popularity record
        popularity = ProductPopularity.query.filter_by(product_id=product_id).first()
        if not popularity:
            return
        
        # Update customer counts with simple queries
        weekly_customers = db.session.query(
            func.count(db.distinct(SalesReport.user_id))
        ).filter(
            SalesReport.product_id == product_id,
            SalesReport.sale_date >= current_week_start
        ).scalar() or 0
        
        monthly_customers = db.session.query(
            func.count(db.distinct(SalesReport.user_id))
        ).filter(
            SalesReport.product_id == product_id,
            SalesReport.sale_date >= current_month_start
        ).scalar() or 0
        
        total_customers = db.session.query(
            func.count(db.distinct(SalesReport.user_id))
        ).filter(
            SalesReport.product_id == product_id
        ).scalar() or 0
        
        popularity.weekly_customers = weekly_customers
        popularity.monthly_customers = monthly_customers
        popularity.total_customers = total_customers

    @staticmethod
    def update_product_rankings():
        """Update product rankings - FIXED VERSION"""
        try:
            from app.models.admin import ProductPopularity
            
            print("🏆 Updating product rankings...")
            
            # Get current period dates
            current_date = datetime.now().date()
            current_week_start = current_date - timedelta(days=current_date.weekday())
            current_month_start = current_date.replace(day=1)
            
            # Reset all flags first
            db.session.query(ProductPopularity).update({
                'is_best_seller': False,
                'is_known_product': False,
                'weekly_rank': 0,
                'monthly_rank': 0
            })
            db.session.commit()
            
            print("📊 Finding best sellers and known products...")
            
            # Update best sellers (top 5 by weekly sales across ALL incubatees)
            best_sellers = ProductPopularity.query.filter(
                ProductPopularity.weekly_sold > 0,
                ProductPopularity.week_start_date >= current_week_start
            ).order_by(
                ProductPopularity.weekly_sold.desc(),
                ProductPopularity.weekly_revenue.desc()
            ).limit(5).all()
            
            print(f"🎯 Found {len(best_sellers)} best sellers")
            for rank, product in enumerate(best_sellers, 1):
                product.is_best_seller = True
                product.weekly_rank = rank
                print(f"   - Best Seller #{rank}: Product {product.product_id} ({product.weekly_sold} sold)")
            
            # Update known products (top 10 by monthly customers across ALL incubatees)
            known_products = ProductPopularity.query.filter(
                ProductPopularity.monthly_customers > 0,
                ProductPopularity.month_start_date >= current_month_start
            ).order_by(
                ProductPopularity.monthly_customers.desc(),
                ProductPopularity.monthly_sold.desc()
            ).limit(10).all()
            
            print(f"🎯 Found {len(known_products)} known products")
            for product in known_products:
                product.is_known_product = True
                print(f"   - Known Product: Product {product.product_id} ({product.monthly_customers} customers)")
            
            db.session.commit()
            print("✅ Rankings updated successfully!")
            
            # Debug: Check what was updated
            best_count = ProductPopularity.query.filter_by(is_best_seller=True).count()
            known_count = ProductPopularity.query.filter_by(is_known_product=True).count()
            print(f"📈 Final counts - Best Sellers: {best_count}, Known Products: {known_count}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating rankings: {str(e)}")
            import traceback
            traceback.print_exc()
            
    @staticmethod
    def force_update_flags():
        """Force update flags based on current data - USE FOR TESTING"""
        try:
            from app.models.admin import ProductPopularity
            
            print("🔄 Force updating product flags...")
            
            # Get products with any sales activity
            products_with_sales = ProductPopularity.query.filter(
                (ProductPopularity.weekly_sold > 0) | 
                (ProductPopularity.monthly_sold > 0) |
                (ProductPopularity.monthly_customers > 0)
            ).all()
            
            print(f"📊 Found {len(products_with_sales)} products with sales activity")
            
            for product in products_with_sales:
                # If has weekly sales, mark as potential best seller
                if product.weekly_sold > 0:
                    product.is_best_seller = True
                    print(f"   - Marking product {product.product_id} as best seller ({product.weekly_sold} weekly sales)")
                
                # If has monthly customers, mark as known product
                if product.monthly_customers > 0:
                    product.is_known_product = True
                    print(f"   - Marking product {product.product_id} as known product ({product.monthly_customers} monthly customers)")
            
            db.session.commit()
            print("✅ Force update complete!")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error in force update: {str(e)}")
            
    @staticmethod
    def get_best_sellers(limit=10):
        """Get current best selling products"""
        from app.models.admin import ProductPopularity
        return ProductPopularity.query.filter(
            ProductPopularity.is_best_seller == True
        ).order_by(
            ProductPopularity.weekly_rank.asc()
        ).limit(limit).all()

    @staticmethod
    def get_popular_products(limit=15):
        """Get popular products (known products)"""
        from app.models.admin import ProductPopularity
        return ProductPopularity.query.filter(
            ProductPopularity.is_known_product == True
        ).order_by(
            ProductPopularity.monthly_customers.desc()
        ).limit(limit).all()